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
from backend.servicios import TotalModificado
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

