"""Operaciones de facturación. Importes en centavos y tasas en puntos básicos."""
import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from backend.servicios import ejecutar

ROOT = Path(__file__).resolve().parents[1]
ROLES = {"admin": "administrador", "operador": "operador", "operador2": "operador", "auditor": "auditor"}

def conectar(ruta):
    db = sqlite3.connect(ruta, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db

def inicializar(db):
    db.executescript((ROOT / "database/local.sql").read_text(encoding="utf-8"))
    db.executemany("INSERT OR IGNORE INTO usuarios_roles VALUES(?,?)", ROLES.items())
    familias = ["Consultoría", "Soporte", "Diseño", "Mantenimiento", "Capacitación"]
    db.executemany("INSERT OR IGNORE INTO servicios VALUES(?,?,?)", [
        (i, f"{familias[(i-1)%5]} · nivel {(i-1)//5+1}", 10000+i*500) for i in range(1,101)])
    db.executemany("INSERT OR IGNORE INTO caracteristicas VALUES(?,?)",
                   [(i, f"Opción {i}") for i in range(1,51)])
    db.executemany("INSERT OR IGNORE INTO caracteristicas_servicio VALUES(?,?)",
                   [(i,(i-1)%50+1) for i in range(1,101)])
    db.execute("INSERT OR IGNORE INTO impuestos_historico VALUES('2000-01-01',1600,400)")
    for nombre in ("admin","operador","operador2"):
        db.execute("INSERT OR IGNORE INTO clientes(nombre,rfc,usuario) VALUES(?,?,?)",
                   ("Cliente de muestra", "XAXX010101000", nombre))
    db.commit()

