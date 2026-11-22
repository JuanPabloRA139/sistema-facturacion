"""Servidor de desarrollo accesible exclusivamente desde esta PC."""
import hashlib
import hmac
import json
import secrets
import sqlite3
import sys
import time
import webbrowser
from threading import Lock
from backend.entrada import leer_objeto
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from backend.local import ROOT, ROLES, conectar, inicializar, operaciones

ARCHIVOS = {"/":"panel.html","/panel.js":"panel.js","/panel.css":"panel.css","/rfc.js":"rfc.js"}
LECTURAS = {"inicio","comprobante","saldos","auditoria"}

class Servidor(ThreadingHTTPServer):
    def __init__(self,ruta,puerto=0):
        self.ruta = ruta
        self.credenciales = {}
        self.sesiones = {}
        self.fallos = []
        self.lock = Lock()
        super().__init__(("127.0.0.1",puerto),Peticion)
        self.origen = f"http://127.0.0.1:{self.server_port}"
        with closing(conectar(ruta)) as db:
            inicializar(db)

    def clave(self,usuario):
        temporal=secrets.token_urlsafe(12)
        self.credenciales[usuario]=hashlib.sha256(temporal.encode()).digest()
        return temporal

class Peticion(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self,*args):
        pass

    def enviar(self,codigo,contenido,tipo="application/json",cookie=None):
        if tipo=="application/json":
            contenido=json.dumps(contenido,ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type",tipo)
        self.send_header("Content-Length",str(len(contenido)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=()")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
        if cookie: self.send_header("Set-Cookie",cookie)
        self.end_headers()
        self.wfile.write(contenido)

    def host_valido(self):
        return self.headers.get("Host")==self.server.origen.removeprefix("http://")

    def do_GET(self):
        if not self.host_valido() or self.path not in ARCHIVOS:
            return self.enviar(404,{"error":"Recurso desconocido."})
        archivo=ROOT/"frontend"/ARCHIVOS[self.path]
        tipos={".html":"text/html",".js":"text/javascript",".css":"text/css"}
        self.enviar(200,archivo.read_bytes(),tipos[archivo.suffix]+"; charset=utf-8")

    def autenticar(self, accion, datos):
        """Bajo el candado de sesiones. La escritura HTTP ocurre después de liberarlo."""
        ahora = time.monotonic()
        sesiones = self.server.sesiones
        for sid, (_, vence) in list(sesiones.items()):
            if vence <= ahora:
                sesiones.pop(sid, None)
        cookies = dict(parte.strip().split("=", 1) for parte in self.headers.get("Cookie", "").split(";") if "=" in parte)
        token = cookies.get("sid")
        if accion == "entrar":
            if set(datos) != {"usuario", "clave"}:
                return None, (400, {"error": "Campos no admitidos."})
            self.server.fallos = [t for t in self.server.fallos if t > ahora-60]
            if len(self.server.fallos) >= 10:
                return None, (429, {"error": "Espera un minuto."})
            usuario, clave = datos["usuario"], datos["clave"]
            valido = isinstance(usuario, str) and isinstance(clave, str) and 0 < len(clave) <= 160
            if not valido or not hmac.compare_digest(hashlib.sha256(clave.encode()).digest(), self.server.credenciales.get(usuario, b"")):
                self.server.fallos.append(ahora)
                return None, (401, {"error": "Credenciales incorrectas."})
            sesiones.pop(token, None)
            token = secrets.token_urlsafe(32)
            sesiones[token] = (usuario, ahora+3600)
            cookie = f"sid={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600"
            return None, (200, {"usuario": usuario}, "application/json", cookie)
        sesion = sesiones.get(token)
        if sesion is None:
            return None, (401, {"error": "Inicia sesión."})
        if accion == "salir":
            if datos:
                return None, (400, {"error": "Campos no admitidos."})
            sesiones.pop(token, None)
            return None, (200, {}, "application/json", "sid=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        return sesion, None

    def do_POST(self):
        if not self.host_valido() or self.headers.get("Origin")!=self.server.origen:
            return self.enviar(403,{"error":"Origen no autorizado."})
        if self.headers.get_content_type()!="application/json":
            return self.enviar(415,{"error":"Se requiere JSON."})
        accion=self.path.removeprefix("/api/")
        if self.path!="/api/"+accion: return self.enviar(404,{})
        try:
            n=int(self.headers.get("Content-Length","0"))
            if not 0<n<=32768: return self.enviar(413,{"error":"Tamaño de petición inválido."})
            p=leer_objeto(self.rfile.read(n))
            with self.server.lock:
                sesion, inmediata = self.autenticar(accion, p)
            if inmediata:
                return self.enviar(*inmediata)
            with closing(conectar(self.server.ruta)) as db, db:
                if accion not in LECTURAS: db.execute("BEGIN IMMEDIATE")
                respuesta=operaciones(db,sesion[0],accion,p)
            return self.enviar(200,respuesta)
        except PermissionError:
            return self.enviar(403,{"error":"Tu rol no permite esta operación."})
        except sqlite3.IntegrityError:
            return self.enviar(409,{"error":"El registro ya existe o contiene referencias inválidas."})
        except (ValueError,TypeError,UnicodeError) as err:
            return self.enviar(400,{"error":str(err) if type(err) is ValueError else "Formato inválido."})
        except sqlite3.Error:
            return self.enviar(503,{"error":"No se pudo completar la operación. Puedes reintentar."})

if __name__=="__main__":
    datos=ROOT/"datos-locales"
    datos.mkdir(exist_ok=True)
    with Servidor(datos/"facturacion.sqlite") as servidor:
        print("Facturación local |",servidor.origen,flush=True)
        for usuario in ROLES: print(usuario,servidor.clave(usuario),flush=True)
        print("Claves temporales para esta sesión. Ctrl+C detiene el servidor.",flush=True)
        if "--abrir" in sys.argv: webbrowser.open(servidor.origen)
        try: servidor.serve_forever()
        except KeyboardInterrupt: pass
