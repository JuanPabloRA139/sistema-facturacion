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
