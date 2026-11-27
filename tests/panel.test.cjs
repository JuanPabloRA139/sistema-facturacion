const test = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');
const fuente = readFileSync(path.join(__dirname, '../frontend/panel.js'), 'utf8');
const fuenteCognito = readFileSync(path.join(__dirname, '../frontend/acceso-aws.js'), 'utf8');

test('Cognito entrega el vencimiento del access token y descarta uno caducado',async()=>{
  const ahora=Math.floor(Date.now()/1000);
  for(const exp of [ahora+300,ahora-1]){
    const parte=Buffer.from(JSON.stringify({exp})).toString('base64url');
    const respuestas=[{dominio:'https://login.example',cliente:'web'},{access_token:'cabecera.'+parte+'.firma'}];
    const contexto=vm.createContext({window:{},location:{origin:'https://app.example',search:'?code=uno&state=caso'},
      document:{getElementById:()=>({})},history:{replaceState(){}}, AbortSignal,URLSearchParams,atob,
      sessionStorage:{getItem:()=>JSON.stringify({verificador:'prueba',estado:'caso',vence:Date.now()+10000}),removeItem(){}},
      fetch:async()=>({ok:true,json:async()=>respuestas.shift()})});
    vm.runInContext(fuenteCognito,contexto);
    const acceso=contexto.window.accesoAWS;
    if(exp>ahora){
      assert.equal(await acceso.preparar(),true);
      assert.equal(acceso.caduca(),exp*1000);
      acceso.reintentar();
    }else await assert.rejects(acceso.preparar(),/caducado/);
    assert.equal(acceso.caduca(),undefined);
    assert.equal(acceso.cabeceras().Authorization,undefined);
  }
});

async function panel(){
  const controles = new Map();
  function control(id){
    if(!controles.has(id)) controles.set(id,{
      dataset:{}, textContent:'', value:'', selectedOptions:[],
      replaceChildren(){this.textContent='';},
      addEventListener(tipo,fn){this[tipo]=fn;},
    });
    return controles.get(id);
  }
  const storage=new Map();
  const eventos={}, documento={}, temporizadores=new Map();
  let indice=0;
  const contexto=vm.createContext({document:{getElementById:control,querySelectorAll:()=>[],addEventListener:(e,f)=>documento[e]=f}, Intl, AbortSignal, crypto:webcrypto,
    window:{addEventListener:(e,f)=>eventos[e]=f,clearTimeout:id=>temporizadores.delete(id),
      setTimeout:fn=>{temporizadores.set(++indice,fn);return indice;}, accesoAWS:{preparar:async()=>false,reintentar(){}}}, FormData:class extends Map {constructor(form){super(form.campos);}},
    sessionStorage:{get length(){return storage.size;},key:i=>[...storage.keys()][i],setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k),getItem:k=>storage.get(k)}});
  const ejecutar=s=>vm.runInContext(s,contexto);
  ejecutar(fuente);
  await new Promise(setImmediate);
  return {control,contexto,ejecutar,storage,eventos,documento,temporizadores};
}

test('La caducidad limpia el comprobante sin hacer otra petición, incluso al reanudar la pestaña',async()=>{
  for(const señal of ['reloj','visibilitychange','pageshow']){
    const {control,ejecutar,documento,eventos,storage,temporizadores}=await panel();
    ejecutar('let reloj=1000; Date.now=()=>reloj; programarCaducidad(3000);');
    control('resultado').textContent='Datos de un comprobante';
    storage.set('facturacion:emision:operador','pendiente');
    ejecutar('reloj=3100;');
    if(señal==='reloj') [...temporizadores.values()][0]();
    if(señal==='visibilitychange') documento.visibilitychange();
    if(señal==='pageshow') eventos.pageshow({persisted:false});
    assert.equal(control('resultado').textContent,'');
    assert.equal(control('acceso').hidden,false);
    assert.equal(storage.size,0);
  }
});

test('Una lectura de la cuenta anterior nunca entrega su comprobante tras cerrar y volver a entrar',async()=>{
  const {control,contexto,ejecutar}=await panel();
  let resolver;
  contexto.window.accesoAWS.cabeceras=()=>({});
  contexto.fetch=()=>new Promise(r=>{resolver=r;});
  const anterior=ejecutar("api('comprobante',{factura:1}).then(f=>el('resultado').textContent=f.rfc)");
  ejecutar('mostrarAcceso(); programarCaducidad(Date.now()+60000);');
  resolver({ok:true,json:async()=>({rfc:'RFC de cuenta anterior'})});
  await assert.rejects(anterior,e=>e.estado===401);
  assert.equal(control('resultado').textContent,'');
});

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

test('Una sesión terminada borra los datos privados y envíos pendientes del panel',async()=>{
  const {control,ejecutar,storage}=await panel();
  const etiquetas=['titulo','detalle-confirmacion','resultado','total','subtotal','identidad','mensaje'];
  etiquetas.forEach(id=>{control(id).textContent='Dato de la cuenta anterior';});
  storage.set('facturacion:emision:uno','solicitud');
  storage.set('facturacion:emision:dos','solicitud');
  storage.set('preferencia-ajena','tema');
  ejecutar('mostrarAcceso()');
  for(const id of etiquetas)assert.equal(control(id).textContent,'');
  assert.deepEqual([...storage.keys()],['preferencia-ajena']);
  assert.equal(control('trabajo').hidden,true);
});

test('Solo la cuenta activa puede retomar el borrador de la pestaña',async()=>{
  const {ejecutar,storage}=await panel();
  storage.set('facturacion:emision:uno','solicitud');
  storage.set('facturacion:emision:dos','otra solicitud');
  ejecutar("limpiarEnviosDeOtrasCuentas('facturacion:emision:uno')");
  assert.deepEqual([...storage.entries()],[['facturacion:emision:uno','solicitud']]);
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

test('Saldos permite paginar, volver y reabrir desde el principio',async()=>{
  const {control,contexto,ejecutar}=await panel();
  const llamadas=[], cursor={vence:'2026-11-01',folio:200};
  contexto.document.createElement=()=>({
    hijos:[],append(...hijos){this.hijos.push(...hijos);},setAttribute(){},
  });
  contexto.peticion=async(accion,p)=>{
    assert.equal(accion,'saldos');
    llamadas.push(JSON.parse(JSON.stringify(p)));
    return p.despues_de?{filas:[{folio:201}],siguiente:null}:{filas:[{folio:1}],siguiente:cursor};
  };
  ejecutar(`datos={usuario:'operador'}; api=peticion; actualizarResumen=()=>{};
    mostrar=(_,n)=>window.contenido=n;tabla=filas=>filas;boton=(texto,accion)=>({texto,accion});
  `);
  function navegacion(){return contexto.window.contenido.hijos[1].hijos.filter(x=>x.accion);}
  await control('antiguedad').onclick();
  assert.equal(contexto.window.contenido.hijos[0][0].folio,1);
  assert.deepEqual(navegacion().map(b=>b.texto),['Siguiente']);
  await navegacion()[0].accion();
  assert.equal(contexto.window.contenido.hijos[0][0].folio,201);
  assert.deepEqual(navegacion().map(b=>b.texto),['Anterior']);
  await navegacion()[0].accion();
  await control('antiguedad').onclick();
  assert.deepEqual(llamadas,[{paginado:true},{paginado:true,despues_de:cursor},{paginado:true},{paginado:true}]);
});

test('Una consulta retrasada de saldos no reaparece tras terminar la sesión',async()=>{
  const {contexto,ejecutar}=await panel();
  let resolver;
  contexto.peticion=()=>new Promise(r=>{resolver=r;});
  ejecutar("datos={usuario:'operador'};api=peticion;mostrar=()=>{window.mostrado=true;};");
  const espera=ejecutar('mostrarSaldos()');
  ejecutar('mostrarAcceso()');
  resolver({filas:[],siguiente:null});await espera;
  assert.equal(contexto.window.mostrado,undefined);
});

