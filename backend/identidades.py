"""Acceso al directorio de usuarios en la segunda instancia PostgreSQL."""
from contextlib import closing
from backend.rds import conectar


def rol_de(usuario):
    with closing(conectar("IDENTITY_SECRET", identidad=True)) as db, closing(db.cursor()) as cur:
        cur.execute("SELECT rol FROM usuarios_roles WHERE usuario_id=%s", (usuario,))
        fila = cur.fetchone()
        if fila is None:
            raise PermissionError
        return fila[0]


def guardar_rol(cursor, usuario, rol):
    cursor.execute("""INSERT INTO usuarios_roles(usuario_id,rol) VALUES (%s,%s)
                      ON CONFLICT (usuario_id) DO UPDATE SET rol=excluded.rol""", (usuario, rol))
