"""Adaptador para RDS. SQL usa pesos decimales; el panel usa centavos enteros."""
import json
import os
import ssl
from uuid import UUID
from decimal import Decimal




def conectar(nombre_secreto="DB_SECRET", *, identidad=False):
    import boto3
    import pg8000.dbapi

    secreto = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ[nombre_secreto])
    cred = json.loads(secreto["SecretString"])
    tls = ssl.create_default_context(cafile=os.environ["RDS_CA_FILE"])
    return pg8000.dbapi.connect(host=os.environ["IDENTITY_HOST" if identidad else "DB_HOST"],
                                database="identidades" if identidad else os.environ["DB_NAME"],
                                user=cred["username"], password=cred["password"],
                                port=int(os.getenv("DB_PORT", "5432")), ssl_context=tls, timeout=5)


def filas(cursor, consulta, params=()):
    cursor.execute(consulta, params)
    nombres = [col[0] for col in cursor.description]
    return [dict(zip(nombres, fila)) for fila in cursor.fetchall()]


def estructura(valor):
    return json.loads(valor, parse_float=Decimal) if isinstance(valor, str) else valor


def centavos(valor):
    return int(Decimal(str(valor)) * 100)


def comprobante(cursor, usuario, folio):
    cursor.execute("CALL generar_comprobante(%s,%s,NULL)", (usuario, folio))
    f = estructura(cursor.fetchone()[0])
    f["id"] = f.pop("folio")
    f["cliente_nombre"] = f.pop("cliente")
    for k in ("subtotal", "descuento", "iva", "retencion", "total", "pagado", "saldo"):
        f[k] = centavos(f[k])
    for linea in f["conceptos"]:
        linea["precio"] = centavos(linea["precio"])
    return f


def preparar_actor(cursor, usuario, consultar_rol):
    # Son límites del servidor PostgreSQL para esta transacción. El timeout
    # del socket por sí solo no fija cuánto tiempo espera PostgreSQL un bloqueo.
    cursor.execute("SET LOCAL lock_timeout = '2s'")
    cursor.execute("SET LOCAL statement_timeout = '4s'")
    cursor.execute("SELECT pg_advisory_xact_lock_shared(hashtextextended(%s, 0))", (usuario,))
    rol = consultar_rol(usuario)
    cursor.execute("SELECT rol FROM usuarios_roles WHERE usuario_id=%s", (usuario,))
    proyeccion = cursor.fetchone()
    if proyeccion is None or proyeccion[0] != rol:
        raise PermissionError
    cursor.execute("SELECT set_config('facturacion.actor',%s,true)", (usuario,))
    return rol


class FacturacionPostgres:
    def __init__(self, cursor, usuario, rol, auditoria):
        self.cursor = cursor
        self.usuario = usuario
        self.rol = rol
        self.auditoria = auditoria

    def inicio(self):
        acceso = (self.usuario, self.rol != "operador")
        return {
            "tasas": filas(self.cursor, """SELECT (iva*10000)::int AS iva, (retencion*10000)::int AS retencion
                FROM impuestos_historico WHERE desde<=CURRENT_DATE ORDER BY desde DESC LIMIT 1""")[0],
            "rol": self.rol, "usuario": self.usuario,
            "servicios": filas(self.cursor, "SELECT servicio_id AS id,nombre,(precio*100)::bigint AS precio FROM servicios ORDER BY servicio_id LIMIT 500"),
            "caracteristicas": filas(self.cursor, "SELECT caracteristica_id AS id,nombre FROM caracteristicas ORDER BY caracteristica_id LIMIT 500"),
            "clientes": filas(self.cursor, "SELECT cliente_id AS id,nombre FROM clientes WHERE responsable=%s OR %s ORDER BY cliente_id DESC LIMIT 500", acceso),
            "facturas": filas(self.cursor, "SELECT folio AS id,fecha,(total*100)::bigint AS total,estado FROM facturas WHERE usuario_id=%s OR %s ORDER BY folio DESC LIMIT 100", acceso),
        }

    def crear_cliente(self, nombre, rfc):
        self.cursor.execute("INSERT INTO clientes(responsable,nombre,rfc) VALUES(%s,%s,%s) RETURNING cliente_id",
                            (self.usuario, nombre, rfc))
        return self.cursor.fetchone()[0]

    def emitir(self, cliente, clave, conceptos):
        self.cursor.execute("CALL emitir_factura(%s,%s,%s::uuid,%s::jsonb,NULL)",
                            (self.usuario, cliente, str(UUID(clave)), json.dumps(conceptos)))
        return self.cursor.fetchone()[0]

    def comprobante(self, folio):
        return comprobante(self.cursor, self.usuario, folio)

    def registrar_pago(self, folio, referencia, importe):
        self.cursor.execute("CALL registrar_pago(%s,%s,%s,%s,NULL,NULL)",
                            (self.usuario, folio, referencia, Decimal(importe) / 100))
        return self.cursor.fetchone()[0]

    def cancelar(self, folio, motivo):
        self.cursor.execute("CALL cancelar_factura(%s,%s,%s)", (self.usuario, folio, motivo))

    def cambiar_tarifa(self, servicio, precio):
        self.cursor.execute("CALL cambiar_tarifa(%s,%s::integer,%s)", (self.usuario, servicio, Decimal(precio) / 100))

    def asignar(self, servicios, caracteristicas):
        self.cursor.execute("CALL asignar_caracteristicas(%s,%s::integer[],%s::integer[])", (self.usuario, servicios, caracteristicas))

    def saldos(self, *, paginado=False, despues_de=None):
        solicitud = json.dumps({"paginado": True, "despues_de": despues_de}) if paginado else None
        self.cursor.execute("CALL antiguedad_saldos(%s,%s::jsonb)", (self.usuario, solicitud))
        reporte = estructura(self.cursor.fetchone()[0])
        for fila in reporte:
            fila["saldo"] = centavos(fila["saldo"])
        return reporte

    def cerrar(self, fecha, mensual):
        self.cursor.execute("CALL cerrar_periodo(%s,%s,%s,NULL)", (self.usuario, fecha, mensual))
        return centavos(self.cursor.fetchone()[0])
