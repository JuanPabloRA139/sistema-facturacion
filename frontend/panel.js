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
