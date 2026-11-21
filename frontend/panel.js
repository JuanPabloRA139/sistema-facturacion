'use strict';
const el = id => document.getElementById(id);
const mxn = new Intl.NumberFormat('es-MX', {style:'currency', currency:'MXN'});
const moneda = centavos => mxn.format(centavos / 100);
const importes = new Set(['precio','saldo','pagado','total','subtotal','descuento','iva','retencion','importe','neto']);
const vistas = {emision:'Nueva factura',clientes:'Clientes',historial:'Facturas y pagos',reportes:'Reportes',catalogo:'Catálogo'};
let datos, conceptos = [], clave, pendiente = false, envio;

function mensaje(texto, error=false) {
  el('mensaje').textContent=texto;
  el('mensaje').dataset.error=String(error);
}
async function api(accion, objeto={}) {
  let respuesta, cuerpo;
  try {
    respuesta=await fetch('/api/'+accion,{method:'POST',headers:{'Content-Type':'application/json',...window.accesoAWS?.cabeceras()},body:JSON.stringify(objeto),signal:AbortSignal.timeout(30000)});
    cuerpo=await respuesta.json();
  } catch {throw new Error('No se recibió la respuesta. Comprueba tu conexión antes de reintentar.');}
  if(!respuesta.ok) {
    if(respuesta.status===401 && accion!=='entrar') mostrarAcceso();
    const error=new Error(cuerpo.error || 'No se pudo completar la operación.');
    error.estado=respuesta.status;
    throw error;
  }
  return cuerpo;
}
function mostrarAcceso(){
  window.accesoAWS?.reintentar();
  datos=undefined; conceptos=[]; envio=undefined; clave=undefined; el('retomar').hidden=true;
  for(const id of ['trabajo','perfil','salida']) el(id).hidden=true;
  el('acceso').hidden=false; el('ruta').textContent='Acceso'; el('estado').textContent='Acceso seguro';
  for(const id of ['menu','resultado','lineas','facturas','cliente','servicio','identidad']) el(id).replaceChildren();
  document.querySelectorAll('#trabajo form, #login').forEach(form=>form.reset());
}
function nodo(tipo,texto){const n=document.createElement(tipo); n.textContent=texto; return n;}
function boton(texto,accion){
  const b=nodo('button',texto); b.type='button'; b.onclick=()=>tarea(accion,b); return b;
}
async function tarea(accion,control){
  if(pendiente) return;
  pendiente=true; mensaje('');
  const bloques=['acceso','retomar','trabajo','menu','perfil','salida'].map(el);
  bloques.forEach(b=>b.inert=true);
  const etiqueta=control?.textContent;
  if(control){control.disabled=true;control.textContent='En proceso…';}
  try {await accion();}
  catch(e){mensaje(e.message,true);}
  finally {
    pendiente=false; bloques.forEach(b=>b.inert=false);
    if(control){control.disabled=false;control.textContent=etiqueta;}
    if(datos) actualizarResumen();
  }
}
