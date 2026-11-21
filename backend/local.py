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

def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)

def numero(valor, minimo=1, maximo=10**9):
    exigir(type(valor) is int and minimo <= valor <= maximo, "Número fuera de rango.")
    return valor

def texto(valor, longitud):
    exigir(isinstance(valor,str) and 0 < len(valor.strip()) <= longitud, "Texto vacío o demasiado largo.")
    return valor.strip()

def filas(db, sql, args=()):
    return [dict(fila) for fila in db.execute(sql,args)]

def evento(db,u,accion,entidad,detalle=""):
    db.execute("INSERT INTO auditoria(usuario,accion,entidad,detalle) VALUES(?,?,?,?)",(u,accion,str(entidad),detalle))

def visible(db, u, fid):
    f = db.execute("SELECT * FROM facturas WHERE id=? AND (usuario=? OR ?)",(numero(fid),u,ROLES[u]!="operador")).fetchone()
    exigir(f is not None,"Factura no disponible.")
    return dict(f)

def pagado(db,fid):
    return db.execute("SELECT coalesce(sum(importe),0) FROM pagos WHERE factura=?",(fid,)).fetchone()[0]

def comprobante(db,u,fid):
    f = visible(db,u,fid)
    f.pop("solicitud"); f.pop("clave")
    f["conceptos"] = filas(db,"SELECT nombre,precio,cantidad FROM detalle_factura WHERE factura=?",(fid,))
    f["cliente_nombre"], f["rfc"] = db.execute("SELECT nombre,rfc FROM clientes WHERE id=?",(f["cliente"],)).fetchone()
    f["pagado"] = pagado(db,fid)
    f["saldo"] = 0 if f["estado"]=="cancelada" else f["total"]-f["pagado"]
    return f

def descuento(subtotal,unidades):
    return (subtotal*5+50)//100 if unidades>=10 else 0

def calcular(db, subtotal, unidades, fecha):
    iva,ret = db.execute("SELECT iva,retencion FROM impuestos_historico WHERE desde<=? ORDER BY desde DESC LIMIT 1",(fecha,)).fetchone()
    desc = descuento(subtotal,unidades)
    base = subtotal-desc
    impuesto, retenido = ((base*t+5000)//10000 for t in (iva,ret))
    return subtotal,desc,impuesto,retenido,base+impuesto-retenido

