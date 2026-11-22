"""Archivos públicos del panel. Todos los datos pasan por la ruta autenticada."""
import json
import os
from pathlib import Path

ARCHIVOS = {"panel.js":"text/javascript","panel.css":"text/css","rfc.js":"text/javascript","acceso-aws.js":"text/javascript"}
CARPETA = Path(__file__).resolve().parents[1]/"frontend"

def handler(event,context):
    ruta = event.get("rawPath","/").lstrip("/")
    dominio = os.environ["LOGIN_DOMAIN"]
    headers = {"Cache-Control":"no-store","Strict-Transport-Security":"max-age=31536000",
               "X-Frame-Options":"DENY","Permissions-Policy":"camera=(), microphone=(), geolocation=()","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff",
               "Content-Security-Policy":f"default-src 'self'; connect-src 'self' {dominio}; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}
    if not ruta:
        cuerpo = (CARPETA/"panel.html").read_text(encoding="utf-8").replace("Entorno local","AWS")
        inicio, fin = cuerpo.index('<section id="acceso">'), cuerpo.index('<div id="trabajo"')
        cuerpo = cuerpo[:inicio] + '<section id="acceso"><h1>Iniciar sesión</h1><p>Accede con tu cuenta de facturación.</p><button class="primario" id="login-aws" disabled>Preparando acceso…</button></section>\n' + cuerpo[fin:]
        cuerpo = cuerpo.replace('<script src="/panel.js">','<script src="/acceso-aws.js"></script><script src="/panel.js">')
        tipo = "text/html"
    elif ruta=="config-publica":
        tipo="application/json"
        cuerpo=json.dumps({"cliente":os.environ["CLIENT_ID"],"dominio":dominio})
    elif ruta in ARCHIVOS:
        tipo=ARCHIVOS[ruta]
        cuerpo=(CARPETA/ruta).read_text(encoding="utf-8")
    else:
        return {"statusCode":404,"headers":headers,"body":"Recurso desconocido"}
    headers["Content-Type"] = tipo+"; charset=utf-8"
    return {"statusCode":200,"headers":headers,"body":cuerpo}
