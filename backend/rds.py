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
    cursor.execute("SELECT pg_advisory_xact_lock_shared(hashtextextended(%s, 0))", (usuario,))
    rol = consultar_rol(usuario)
    cursor.execute("SELECT rol FROM usuarios_roles WHERE usuario_id=%s", (usuario,))
    proyeccion = cursor.fetchone()
    if proyeccion is None or proyeccion[0] != rol:
        raise PermissionError
    cursor.execute("SELECT set_config('facturacion.actor',%s,true)", (usuario,))
    return rol


