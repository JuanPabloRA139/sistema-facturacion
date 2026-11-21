// Ejecuta el panel real con una API en memoria en un perfil de navegador temporal.
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {spawnSync} = require('node:child_process');
const carpeta = path.join(__dirname, '..', 'frontend');
const leer = nombre => fs.readFileSync(path.join(carpeta, nombre), 'utf8');
const navegador = process.argv[2];
if (!navegador) throw new Error('Indica la ruta de Chrome o Edge.');

function preparar(){
  const estado = window.prueba = {accesos:0, envios:[], autenticado:false};
  window.fetch = async(url, opciones)=>{
    const accion=url.split('/').pop(), p=JSON.parse(opciones.body);
    const respuesta=(valor,status=200)=>new Response(JSON.stringify(valor),{status});
    if(accion==='entrar'){estado.accesos++;estado.autenticado=true;return respuesta({});}
    if(!estado.autenticado)return respuesta({error:'Inicia sesión.'},401);
    if(accion==='inicio')return respuesta({rol:'operador',usuario:'prueba-ui',tasas:{iva:1600,retencion:400},
      clientes:[{id:1,nombre:"O'Connor & Hijos <Norte>"}],servicios:[{id:1,nombre:'Consultoría',precio:10500}],caracteristicas:[],facturas:[]});
    if(accion==='emitir'){
      estado.envios.push(p);
      if(estado.envios.length===1)throw new Error('Respuesta interrumpida');
      return respuesta({id:7,fecha:'2026-11-21',cliente_nombre:"O'Connor & Hijos <Norte>",rfc:'XAXX010101000',
        conceptos:[{nombre:'Consultoría',precio:10500,cantidad:1}],estado:'emitida',subtotal:10500,descuento:0,
        iva:1680,retencion:420,total:11760,saldo:11760,pagado:0});
    }
    throw new Error('Acción inesperada');
  };
}
async function recorrido(){
  const id=n=>document.getElementById(n);
  const pausa=()=>new Promise(r=>setTimeout(r,10));
  const afirmar=(condicion,texto)=>{if(!condicion)throw new Error(texto);};
  const esperar=async(condicion,texto)=>{for(let i=0;i<90;i++){if(condicion())return;await pausa();}throw new Error(texto);};
  try {
    await esperar(()=>!id('acceso').inert,'inicio bloqueado');
    const login=id('login');login.elements.clave.value='clave temporal';
    login.requestSubmit();login.requestSubmit();
    await esperar(()=>!id('trabajo').hidden&&!id('trabajo').inert,'acceso incompleto');
    afirmar(prueba.accesos===1,'acceso repetido');
    id('cliente').value='1';id('cliente').dispatchEvent(new Event('change'));
    afirmar(id('cliente').selectedOptions[0].textContent==="O'Connor & Hijos <Norte>",'nombre alterado');
    afirmar(id('emitir').disabled,'emisión vacía disponible');
    id('abrir-concepto').click();id('agregar').requestSubmit();
    await esperar(()=>!id('emitir').disabled,'concepto ausente');
    afirmar(id('total').textContent.includes('117.60'),'total incorrecto');
    id('emitir').click();id('emitir').click();await pausa();
    afirmar(id('confirmacion').open&&prueba.envios.length===0,'falta confirmación previa');
    id('confirmacion').querySelector('[value=volver]').click();await pausa();
    afirmar(prueba.envios.length===0,'volver envió la factura');
    id('emitir').click();id('aceptar').click();await pausa();
    await esperar(()=>id('emitir').textContent==='Verificar emisión','no permite recuperar');
    afirmar(prueba.envios.length===1&&id('cliente').disabled,'borrador pendiente editable');
    id('emitir').click();id('emitir').click();
    await esperar(()=>id('mensaje').textContent.includes('Factura 7 emitida'),'sin confirmación final');
    afirmar(prueba.envios.length===2&&JSON.stringify(prueba.envios[0])===JSON.stringify(prueba.envios[1]),'cambió la solicitud al reintentar');
    afirmar(!id('resultado').querySelector('norte')&&id('resultado').textContent.includes('<Norte>'),'el nombre dejó de ser texto');
    afirmar(id('emitir').disabled&&!sessionStorage.getItem('facturacion:emision:prueba-ui'),'no se limpió el envío');
    afirmar(document.documentElement.scrollWidth<=innerWidth+1,'desbordamiento horizontal');
    document.body.dataset.veredicto='aprobado';
  } catch(e){document.body.dataset.veredicto='fallo '+e.message;}
}
const temporal=fs.mkdtempSync(path.join(os.tmpdir(),'facturacion-ui-'));
try {
  const script=codigo=>'<script>'+codigo+'</script>';
  const pagina=leer('panel.html').replace('<link rel="stylesheet" href="/panel.css">','<style>'+leer('panel.css')+'</style>')
    .replace('<script src="/rfc.js"></script>',()=>script('('+preparar+')()')+script(leer('rfc.js')))
    .replace('<script src="/panel.js"></script>',()=>script(leer('panel.js'))+script('('+recorrido+')()'));
  const archivo=path.join(temporal,'panel.html');
  fs.writeFileSync(archivo,pagina);
  for(const ancho of [1440,390]){
    const r=spawnSync(navegador,['--headless','--disable-gpu','--no-first-run','--disable-extensions',
      '--disable-background-networking','--no-proxy-server','--user-data-dir='+path.join(temporal,'perfil'+ancho),
      '--window-size='+ancho+',900','--virtual-time-budget=4000','--dump-dom',pathToFileURL(archivo).href],
      {encoding:'utf8',timeout:30000,windowsHide:true,maxBuffer:4*1024*1024});
    const veredicto=r.stdout?.match(/<body[^>]*data-veredicto="([^"]+)"/)?.[1];
    if(veredicto!=='aprobado')throw new Error(veredicto||r.error?.message||'El navegador terminó sin resultado. Código '+r.status+' '+(r.stderr||'').slice(-300));
    console.log('Panel verificado con ventana de '+ancho+' px.');
  }
} finally {fs.rmSync(temporal,{recursive:true,force:true,maxRetries:3});}

