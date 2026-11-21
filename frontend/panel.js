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
function formulario(id,accion){
  el(id).addEventListener('submit',e=>{
    e.preventDefault();
    const campos=Object.fromEntries(new FormData(e.target));
    tarea(()=>{
      for(const nombre of ['nombre','rfc','referencia','motivo','periodo']){
        if(!(nombre in campos))continue;
        if(/[\p{Cc}\p{Cf}\p{Cs}]/u.test(campos[nombre])||!campos[nombre].trim()){
          throw new Error('Revisa el campo '+nombre+'. Debe contener texto visible.');
        }
        campos[nombre]=campos[nombre].trim();
      }
      return accion(campos,e.target);
    },e.submitter);
  });
}
function confirmar(titulo,detalle,etiqueta){
  const d=el('confirmacion');
  el('pregunta').textContent=titulo;el('detalle-confirmacion').textContent=detalle;el('aceptar').textContent=etiqueta;
  d.returnValue='volver';
  return new Promise(resolve=>{d.addEventListener('close',()=>resolve(d.returnValue==='aceptar'),{once:true});d.showModal();});
}
function tabla(registros,seleccionar){
  if(!registros.length)return nodo('p','Sin registros.');
  const t=document.createElement('table'), encabezado=t.createTHead().insertRow();
  const campos=Object.keys(registros[0]);
  campos.forEach(k=>encabezado.append(nodo('th',k.replaceAll('_',' '))));
  if(seleccionar) encabezado.append(nodo('th','Comprobante'));
  const body=t.createTBody();
  for(const fila of registros){
    const tr=body.insertRow();
    for(const k of campos) tr.insertCell().textContent=importes.has(k)?moneda(fila[k]):fila[k];
    if(seleccionar) tr.insertCell().append(boton('Ver',async()=>seleccionar(fila.id)));
  }
  return t;
}
function mostrar(titulo,contenido){
  el('salida').hidden=false; el('titulo').textContent=titulo; el('resultado').replaceChildren(contenido);
  el('salida').scrollIntoView({block:'nearest'});
}
function verFactura(f){
  const detalle=document.createElement('div');
  detalle.append(nodo('p',f.cliente_nombre+' · '+f.rfc+' · '+f.estado),tabla(f.conceptos));
  for(const k of ['subtotal','descuento','iva','retencion','total','pagado','saldo']) detalle.append(nodo('p',k+' · '+moneda(f[k])));
  const json=document.createElement('details');
  json.append(nodo('summary','Ver comprobante en JSON'),nodo('pre',JSON.stringify(f,null,2)));
  detalle.append(json); mostrar('Factura '+f.id+' · '+f.fecha,detalle);
}
function opciones(select,items,precios=false){
  const anterior=new Set(Array.from(select.selectedOptions,o=>o.value));
  select.replaceChildren(...items.map(i=>new Option(i.nombre+(precios?' · '+moneda(i.precio):''),i.id)));
  if(select.id==='cliente'){
    const vacio=new Option('Seleccionar cliente','');
    select.add(vacio,0);
    select.value='';
  }
  for(const o of select.options) if(anterior.has(o.value)) o.selected=true;
}
function verVista(id){
  for(const k of Object.keys(vistas)) el(k).hidden=k!==id;
  el('menu').querySelectorAll('[data-vista]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.vista===id)));
  el('ruta').textContent=vistas[id]; el('salida').hidden=true;
}
async function recargar(){
  datos=await api('inicio');
  opciones(el('cliente'),datos.clientes); opciones(el('servicio'),datos.servicios,true);
  opciones(el('tarifas').elements.servicio,datos.servicios,true);
  opciones(el('lote').elements.servicios,datos.servicios); opciones(el('lote').elements.caracteristicas,datos.caracteristicas);
  el('facturas').replaceChildren(tabla(datos.facturas,async id=>verFactura(await api('comprobante',{factura:id}))));
  actualizarResumen();
}
async function realizado(texto){
  mensaje(texto);
  try {await recargar();}
  catch {mensaje(texto+' No se pudo actualizar la vista. Vuelve a entrar para consultarla.',true);}
}
const llaveEnvio=()=> 'facturacion:emision:'+datos.usuario;
async function entrar(){
  await recargar(); el('acceso').hidden=true; el('trabajo').hidden=false; el('perfil').hidden=false;
  el('estado').textContent='Sesión activa'; el('identidad').textContent=datos.rol[0].toUpperCase()+datos.rol.slice(1);
  const admin=datos.rol==='administrador',auditor=datos.rol==='auditor';
  const menu=el('menu');menu.replaceChildren();
  for(const [id,etiqueta] of Object.entries(vistas)){
    if((id==='catalogo'&&!admin)||(['clientes','emision'].includes(id)&&auditor)) continue;
    const b=boton(etiqueta,()=>verVista(id));b.dataset.vista=id;menu.append(b);
  }
  el('sec-cobro').hidden=auditor;el('sec-cancelacion').hidden=!admin;el('sec-cerrar').hidden=!admin;el('eventos').hidden=datos.rol==='operador';
  verVista(auditor?'historial':'emision');
  clave=crypto.randomUUID();
  if(!auditor){
    let previo;
    try {previo=sessionStorage.getItem(llaveEnvio());} catch {mensaje('Habilita el almacenamiento de la pestaña para emitir facturas.',true);}
    if(previo){
      const p=JSON.parse(previo);
      if(Array.isArray(p.conceptos)&&typeof p.clave==='string'){
        envio=p;conceptos=p.conceptos;clave=p.clave;el('cliente').value=String(p.cliente);
        mensaje('Hay una emisión pendiente de verificar. Recupera el resultado con la misma referencia.');
      }
    }
  }
  actualizarResumen();
}
el('salir').onclick=()=>tarea(async()=>{
  if(!await confirmar('¿Cerrar sesión?',conceptos.length&&!envio?'Se descartarán los conceptos del borrador.':'Para continuar tendrás que identificarte de nuevo.','Cerrar sesión')) return;
  if(window.accesoAWS) return window.accesoAWS.salir();
  await api('salir');mostrarAcceso();mensaje('Sesión cerrada.');
});
async function cargarSesion(){
  try {
    await entrar();
    el('retomar').hidden=true;
    if(!envio)mensaje('Sesión iniciada.');
  } catch(e){
    if(e.estado===403)mostrarAcceso();
    if(!e.estado || e.estado>=500){
      el('retomar').hidden=false;
      el('acceso').hidden=true;
      throw new Error('No se pudo cargar el panel. Vuelve a cargar tu sesión.');
    }
    throw e;
  }
}
el('retomar').onclick=()=>tarea(cargarSesion,el('retomar'));
if(el('login'))formulario('login',async(p,form)=>{
  await api('entrar',p);
  form.elements.clave.value='';
  await cargarSesion();
});
function reiniciar(){conceptos=[];envio=undefined;clave=crypto.randomUUID();el('agregar').hidden=true;}
function actualizarResumen(){
  const lista=el('lineas');lista.replaceChildren();
  let subtotal=0, unidades=0;
  for(const [i,l] of conceptos.entries()){
    const s=datos.servicios.find(s=>s.id===l.servicio);
    const importe=(s?.precio || 0)*l.cantidad;
    subtotal+=importe;unidades+=l.cantidad;
    const tr=lista.insertRow();
    for(const valor of [s?.nombre || 'Servicio no disponible',l.cantidad,moneda(s?.precio || 0),moneda(importe)]) tr.insertCell().textContent=valor;
    const quitar=boton('×',()=>{conceptos.splice(i,1);clave=crypto.randomUUID();});
    quitar.className='quitar';quitar.setAttribute('aria-label','Quitar concepto '+(i+1));quitar.disabled=Boolean(envio);tr.insertCell().append(quitar);
  }
  if(!conceptos.length){const td=lista.insertRow().insertCell();td.colSpan=5;td.className='vacio';td.textContent='Agrega un servicio para calcular la factura.';}
  const descuento=unidades>=10?Math.floor((subtotal*5+50)/100):0;
  const impuesto=tasa=>Math.floor(((subtotal-descuento)*tasa+5000)/10000);
  const iva=impuesto(datos.tasas.iva),retencion=impuesto(datos.tasas.retencion);
  const total=subtotal-descuento+iva-retencion;
  for(const [id,valor] of Object.entries({subtotal,descuento,iva,retencion,total})) el(id).textContent=moneda(['retencion','descuento'].includes(id)&&valor?-valor:valor);
  el('et-iva').textContent='IVA ('+datos.tasas.iva/100+' %)';el('et-retencion').textContent='Retención ('+datos.tasas.retencion/100+' %)';
  el('emitir').disabled=!envio&&(!conceptos.length||!el('cliente').value);
  el('emitir').textContent=envio?'Verificar emisión':'Emitir factura';
  el('vaciar').disabled=!conceptos.length;el('cliente').disabled=Boolean(envio);
  el('abrir-concepto').disabled=Boolean(envio);if(envio)el('agregar').hidden=true;
  return total;
}
el('abrir-concepto').onclick=()=>{el('agregar').hidden=!el('agregar').hidden;if(!el('agregar').hidden)el('servicio').focus();};
formulario('agregar',()=>{
  if(envio||conceptos.length>=30)throw new Error('Revisa el borrador. El máximo es de 30 conceptos.');
  const servicio=Number(el('servicio').value),cantidad=Number(el('cantidad').value);
  if(!datos.servicios.some(s=>s.id===servicio)||!Number.isInteger(cantidad)||cantidad<1||cantidad>999)throw new Error('Selecciona un servicio y una cantidad de 1 a 999.');
  conceptos.push({servicio,cantidad});clave=crypto.randomUUID();el('agregar').hidden=true;el('cantidad').value='1';mensaje('Concepto agregado.');
});
el('vaciar').onclick=()=>tarea(async()=>{
  if(!await confirmar('¿Descartar el borrador?',envio?'Consulta las facturas recientes antes de volver a emitir. La operación anterior pudo completarse.':'Se quitarán todos los conceptos de esta factura.','Descartar'))return;
  sessionStorage.removeItem(llaveEnvio());reiniciar();mensaje('Borrador descartado.');
});
el('cliente').onchange=()=>{clave=crypto.randomUUID();actualizarResumen();};
