"""Inicialización privada. Esta Lambda carece de ruta HTTP."""
import json
import os
from contextlib import closing
from pathlib import Path
from uuid import UUID
import boto3
from backend.rds import conectar
from backend.identidades import guardar_rol

SCRIPTS = ["01_catalogo","02_datos_catalogo","03_facturacion","04_procedimientos","06_operaciones","08_auditoria"]
SQL_DIR = Path(__file__).resolve().parents[1] / "database"


def autorizar(db, cur, usuario, rol):
    if rol not in ("administrador", "operador", "auditor"):
        raise ValueError("Rol desconocido")
    cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (usuario,))
    guardar_rol(cur, usuario, rol)
    with closing(conectar("IDENTITY_MASTER_SECRET", identidad=True)) as identidad:
        with closing(identidad.cursor()) as destino:
            guardar_rol(destino, usuario, rol)
        identidad.commit()
    db.commit()
    return {"autorizado": True}


def inicializar_directorio(origen):
    with closing(conectar("IDENTITY_MASTER_SECRET", identidad=True)) as identidad, closing(identidad.cursor()) as cur:
        cur.execute((SQL_DIR / "09_identidades.sql").read_text(encoding="utf-8-sig"))
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname='identidad_lectura'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE identidad_lectura LOGIN")
        secreto = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["IDENTITY_SECRET"])
        cur.execute("SELECT quote_literal(%s::text)", (json.loads(secreto["SecretString"])["password"],))
        cur.execute("ALTER ROLE identidad_lectura PASSWORD " + cur.fetchone()[0])
        cur.execute("GRANT USAGE ON SCHEMA public TO identidad_lectura")
        cur.execute("GRANT SELECT ON usuarios_roles TO identidad_lectura")
        cur.execute("""INSERT INTO migraciones VALUES ('directorio_inicial')
                       ON CONFLICT DO NOTHING RETURNING nombre""")
        if cur.fetchone():
            origen.execute("SELECT usuario_id,rol FROM usuarios_roles")
            for usuario, rol in origen.fetchall():
                cur.execute("""INSERT INTO usuarios_roles VALUES (%s,%s)
                               ON CONFLICT (usuario_id) DO NOTHING""", (usuario, rol))
        identidad.commit()


