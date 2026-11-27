'use strict';
// Solo el verificador de PKCE y el estado viven durante la redirección.
window.accesoAWS = (() => {
  let token, vence, config;
  const retorno = location.origin + '/';
  const base64url = bytes => btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
  const azar = () => base64url(crypto.getRandomValues(new Uint8Array(32)));
  const boton = document.getElementById('login-aws');
  function estadoBoton(texto, ocupado) {
    boton.disabled = ocupado;
    boton.textContent = texto;
  }
  function disponible() {
    estadoBoton('Entrar con Cognito', false);
  }
  async function iniciar() {
    if (boton.disabled) return;
    estadoBoton('Abriendo Cognito…', true);
    const verificador = azar(), estado = azar();
    sessionStorage.setItem('oauth-pendiente',JSON.stringify({verificador,estado,vence:Date.now()+600000}));
    const digest = await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verificador));
    const params = new URLSearchParams({response_type:'code',client_id:config.cliente,redirect_uri:retorno,
      scope:'openid',state:estado,code_challenge:base64url(new Uint8Array(digest)),code_challenge_method:'S256'});
    location.assign(config.dominio+'/oauth2/authorize?'+params);
  }
  async function preparar() {
    const res = await fetch('/config-publica',{signal:AbortSignal.timeout(20000)});
    if (!res.ok) throw new Error('No se pudo cargar el acceso.');
    config = await res.json();
    boton.onclick = () => iniciar().catch(() => {
      disponible();
      document.getElementById('mensaje').textContent='No se pudo iniciar sesión.';
    });
    const params = new URLSearchParams(location.search);
    if (!params.has('code') && !params.has('error')) {
      disponible();
      return false;
    }
    estadoBoton('Comprobando sesión…', true);
    history.replaceState({},'',retorno);
    const guardado = JSON.parse(sessionStorage.getItem('oauth-pendiente') || 'null');
    sessionStorage.removeItem('oauth-pendiente');
    if (!guardado || !(guardado.vence>Date.now()) || params.get('state')!==guardado.estado || params.has('error'))
      throw new Error('El acceso no se completó. Vuelve a entrar.');
    const body = new URLSearchParams({grant_type:'authorization_code',client_id:config.cliente,
      code:params.get('code'),redirect_uri:retorno,code_verifier:guardado.verificador});
    const r=await fetch(config.dominio+'/oauth2/token',{method:'POST',body,signal:AbortSignal.timeout(20000)});
    if(!r.ok) throw new Error('No se pudo completar el acceso.');
    const credencial=await r.json();
    // La API valida la firma. El navegador usa exp exclusivamente para borrar su vista a tiempo.
    const contenido=credencial.access_token?.split('.')[1];
    if(!contenido)throw new Error('No se recibió la sesión.');
    const {exp}=JSON.parse(atob(contenido.replaceAll('-','+').replaceAll('_','/')));
    if(!Number.isSafeInteger(exp)||exp*1000<=Date.now())throw new Error('La sesión ha caducado.');
    vence=exp*1000;
    token=credencial.access_token;
    estadoBoton('Cargando tu menú…', true);
    return true;
  }
  function salir(){
    token=vence=undefined;
    location.assign(config.dominio+'/logout?'+new URLSearchParams({client_id:config.cliente,logout_uri:retorno}));
  }
  function reintentar() {
    token=vence=undefined;
    if (config && boton.onclick) disponible();
    else {
      estadoBoton('Reintentar acceso', false);
      boton.onclick = () => location.reload();
    }
  }
  return {preparar,salir,reintentar,caduca:()=>vence,cabeceras:()=>token ? {Authorization:'Bearer '+token} : {}};
})();
