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


