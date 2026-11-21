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

def guardar_factura(db, u, cliente, clave, renglones):
    solicitud = json.dumps([cliente,renglones],sort_keys=True)
    anterior = db.execute("SELECT id,solicitud FROM facturas WHERE usuario=? AND clave=?",(u,clave)).fetchone()
    if anterior:
        exigir(anterior["solicitud"]==solicitud,"La clave corresponde a otra emisión.")
        return anterior["id"]
    exigir(db.execute("SELECT 1 FROM clientes WHERE id=? AND (usuario=? OR ?)",(cliente,u,ROLES[u]=="administrador")).fetchone(),"Cliente no disponible.")
    conceptos = []
    for linea in renglones:
        exigir(isinstance(linea,dict),"Concepto inválido.")
        sid = numero(linea.get("servicio"))
        s = db.execute("SELECT nombre,precio FROM servicios WHERE id=?",(sid,)).fetchone()
        exigir(s,"Servicio desconocido.")
        conceptos.append((sid,s["nombre"],s["precio"],numero(linea.get("cantidad"),1,999)))
    hoy = date.today()
    totales = calcular(db,sum(c[2]*c[3] for c in conceptos),sum(c[3] for c in conceptos),hoy.isoformat())
    fid = db.execute("INSERT INTO facturas(cliente,usuario,clave,solicitud,fecha,vence,subtotal,descuento,iva,retencion,total) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (cliente,u,clave,solicitud,str(hoy),str(hoy+timedelta(days=30)),*totales)).lastrowid
    db.executemany("INSERT INTO detalle_factura VALUES(?,?,?,?,?)",[(fid,*c) for c in conceptos])
    db.execute("INSERT INTO movimientos(fecha,factura,concepto,importe) VALUES(?,?,'emision',?)",(str(hoy),fid,totales[-1]))
    evento(db,u,"emisión",fid)
    return fid

class FacturacionSQLite:
    def __init__(self, db, usuario):
        self.db = db
        self.usuario = usuario

    def emitir(self, cliente, clave, conceptos):
        return guardar_factura(self.db, self.usuario, cliente, clave, conceptos)

    def comprobante(self, folio):
        return comprobante(self.db, self.usuario, folio)

    def inicio(self):
        tasas = self.db.execute("SELECT iva, retencion FROM impuestos_historico WHERE desde<=? ORDER BY desde DESC LIMIT 1", (date.today().isoformat(),)).fetchone()
        return dict(tasas=dict(tasas),usuario=self.usuario,rol=ROLES[self.usuario],servicios=filas(self.db,"SELECT * FROM servicios ORDER BY id"),
            clientes=filas(self.db,"SELECT id,nombre FROM clientes WHERE usuario=? OR ? ORDER BY id",(self.usuario,ROLES[self.usuario]!="operador")),
            caracteristicas=filas(self.db,"SELECT * FROM caracteristicas ORDER BY id"),
            facturas=filas(self.db,"SELECT id,fecha,total,estado FROM facturas WHERE usuario=? OR ? ORDER BY id DESC LIMIT 100",(self.usuario,ROLES[self.usuario]!="operador")))

    def crear_cliente(self, nombre, rfc):
        cid=self.db.execute("INSERT INTO clientes(nombre,rfc,usuario) VALUES(?,?,?)",(nombre,rfc,self.usuario)).lastrowid
        return cid

    def registrar_pago(self, folio, ref, importe):
        f=visible(self.db,self.usuario,folio)
        previo=self.db.execute("SELECT importe FROM pagos WHERE factura=? AND referencia=?",(f["id"],ref)).fetchone()
        if previo:
            exigir(previo[0]==importe,"Referencia ya utilizada con otro importe.")
        else:
            exigir(f["estado"] != "cancelada", "La factura está cancelada y no admite pagos.")
            saldo = f["total"] - pagado(self.db, f["id"])
            exigir(importe <= saldo, "El pago supera el saldo pendiente de la factura.")
            self.db.execute("INSERT INTO pagos(factura,referencia,importe) VALUES(?,?,?)",(f["id"],ref,importe))
            estado="pagada" if pagado(self.db,f["id"])==f["total"] else "parcial"
            self.db.execute("UPDATE facturas SET estado=? WHERE id=?",(estado,f["id"]))
            evento(self.db,self.usuario,"pago",f["id"])
        return previo is not None

    def cancelar(self, folio, motivo):
        f=visible(self.db,self.usuario,folio)
        if f["estado"]!="cancelada":
            exigir(pagado(self.db,f["id"])==0,"Solo se pueden cancelar facturas sin pagos registrados.")
            self.db.execute("UPDATE facturas SET estado='cancelada' WHERE id=?",(f["id"],))
            self.db.execute("INSERT INTO movimientos(fecha,factura,concepto,importe) VALUES(?,?,'reversion',?)",(str(date.today()),f["id"],-f["total"]))
            evento(self.db,self.usuario,"cancelación",f["id"],motivo)

    def cambiar_tarifa(self, sid, precio):
        antes=self.db.execute("SELECT precio FROM servicios WHERE id=?",(sid,)).fetchone()
        exigir(antes,"Servicio desconocido.")
        if antes[0] == precio:
            return
        self.db.execute("UPDATE servicios SET precio=? WHERE id=?",(precio,sid))
        evento(self.db,self.usuario,"tarifa",sid,f"{antes[0]} → {precio} centavos")

    def asignar(self, servicios, caracteristicas):
        self.db.executemany("INSERT OR IGNORE INTO caracteristicas_servicio VALUES(?,?)",[(numero(s),numero(c)) for s in servicios for c in caracteristicas])

    def saldos(self):
        return filas(self.db,"""SELECT f.id AS folio,f.vence,max(0,CAST(julianday(?) - julianday(f.vence) AS INTEGER)) AS dias_vencidos,
           f.total-coalesce(sum(p.importe),0) AS saldo FROM facturas f LEFT JOIN pagos p ON p.factura=f.id
           WHERE f.estado IN ('emitida','parcial') AND (f.usuario=? OR ?) GROUP BY f.id ORDER BY f.vence LIMIT 200""",(str(date.today()),self.usuario,ROLES[self.usuario]!="operador"))

    def cerrar(self, inicio, mensual):
        fin=inicio+timedelta(days=1) if not mensual else (inicio.replace(day=28)+timedelta(days=4)).replace(day=1)
        exigir(fin<=date.today(),"El periodo debe haber terminado.")
        periodo = inicio.isoformat()[:7] if mensual else inicio.isoformat()
        self.db.execute("""INSERT OR IGNORE INTO cierres(periodo,neto) SELECT ?,coalesce(sum(importe),0) FROM movimientos WHERE fecha>=? AND fecha<?""",(periodo,str(inicio),str(fin)))
        return self.db.execute("SELECT neto FROM cierres WHERE periodo=?",(periodo,)).fetchone()[0]

    def auditoria(self):
        return filas(self.db,"SELECT * FROM auditoria ORDER BY id DESC LIMIT 100")


def operaciones(db, usuario, accion, datos):
    return ejecutar(FacturacionSQLite(db, usuario), ROLES[usuario], accion, datos)
