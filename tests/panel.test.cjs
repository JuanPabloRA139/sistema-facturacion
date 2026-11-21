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

