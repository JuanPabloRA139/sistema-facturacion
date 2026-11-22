const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const fuente = readFileSync(path.join(__dirname, '../frontend/panel.js'), 'utf8');

async function panel(){
  const controles = new Map();
  function control(id){
    if(!controles.has(id)) controles.set(id,{
      dataset:{}, textContent:'', value:'', selectedOptions:[],
      addEventListener(tipo,fn){this[tipo]=fn;},
    });
    return controles.get(id);
  }
  const storage=new Map();
  const contexto=vm.createContext({document:{getElementById:control}, Intl, AbortSignal, crypto:webcrypto,
    window:{addEventListener(){},accesoAWS:{preparar:async()=>false}}, FormData:class extends Map {constructor(form){super(form.campos);}},
    sessionStorage:{setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k),getItem:k=>storage.get(k)}});
  const ejecutar=s=>vm.runInContext(s,contexto);
  ejecutar(fuente);
  await new Promise(setImmediate);
  return {control,contexto,ejecutar,storage};
}

test('El doble envío del formulario de acceso inicia una sola petición', async()=>{
  const {control,contexto,ejecutar}=await panel();
  let llamadas=0, resolver;
  contexto.peticion=()=>{llamadas++;return new Promise(r=>{resolver=r;});};
  ejecutar("api=peticion; entrar=async()=>{};");
  const form=control('login'), enviar=control('boton-entrar');
  form.campos=[['usuario','operador'],['clave','temporal']];form.elements={clave:{value:'temporal'}};
  const evento={target:form,submitter:enviar,preventDefault(){}};
  form.submit(evento);form.submit(evento);
  assert.equal(llamadas,1);assert.equal(enviar.disabled,true);
  resolver();await new Promise(setImmediate);
  assert.equal(enviar.disabled,false);assert.equal(form.elements.clave.value,'');
});

test('Emitir requiere confirmación y recupera el mismo envío tras una interrupción',async()=>{
  const {control,contexto,ejecutar,storage}=await panel();
  const enviadas=[];let aceptar=false;
  contexto.decidir=async()=>aceptar;
  contexto.peticion=async(_,p)=>{
    enviadas.push(JSON.stringify(p));
    if(enviadas.length===1)throw new Error('Respuesta interrumpida');
    return {id:42,total:11760};
  };
  ejecutar(`datos={usuario:'operador'};conceptos=[{servicio:1,cantidad:1}];clave=crypto.randomUUID();
    actualizarResumen=()=>11760; confirmar=decidir;api=peticion;verFactura=()=>{};realizado=async texto=>mensaje(texto);`);
  control('cliente').selectedOptions=[{textContent:'Empresa',value:'1'}];
  const emitir=control('emitir').onclick;
  await emitir();assert.equal(enviadas.length,0);
  aceptar=true;await Promise.all([emitir(),emitir()]);assert.equal(enviadas.length,1);
  assert.equal(storage.size,1);
  await Promise.all([emitir(),emitir()]);assert.equal(enviadas.length,2);
  assert.equal(enviadas[0],enviadas[1]);assert.equal(storage.size,0);
  assert.match(control('mensaje').textContent,/Factura 42 emitida/);
});

test('Los importes monetarios se convierten exactamente a centavos',async()=>{
  const {ejecutar}=await panel();
  assert.equal(ejecutar("centavos('1.01')"),101);
  assert.equal(ejecutar("centavos('10.5')"),1050);
  for(const s of ['1.005','1e3','-1',''])assert.throws(()=>ejecutar('centavos('+JSON.stringify(s)+')'));
});


test('Una sesión aceptada puede recargar el panel sin volver a enviar la clave', async()=>{
  const {control,contexto,ejecutar}=await panel();
  let autenticaciones=0,lecturas=0;
  contexto.autenticar=async()=>{autenticaciones++;};
  contexto.cargar=async()=>{if(++lecturas===1)throw new Error('Interrupción');};
  ejecutar('api=autenticar; entrar=cargar;');
  const form=control('login');
  form.campos=[['usuario','operador'],['clave','temporal']];form.elements={clave:{value:'temporal'}};
  form.submit({target:form,submitter:control('enviar'),preventDefault(){}});
  await new Promise(setImmediate);
  assert.equal(control('retomar').hidden,false);
  await control('retomar').onclick();
  assert.equal(control('retomar').hidden,true);
  assert.equal(autenticaciones,1);
  assert.equal(lecturas,2);
});
