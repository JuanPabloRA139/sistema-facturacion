import unittest

from backend.local import conectar, inicializar, operaciones


class PrivacidadCancelacion(unittest.TestCase):
    def setUp(self):
        self.db = conectar(":memory:")
        self.addCleanup(self.db.close)

    def emitir(self):
        cliente = operaciones(self.db, "operador", "inicio", {})["clientes"][0]["id"]
        with self.db:
            factura = operaciones(self.db, "operador", "emitir", {
                "cliente": cliente, "clave": "prueba-cancelacion",
                "conceptos": [{"servicio": 1, "cantidad": 1}],
            })
        return factura["id"]

    def test_motivo_se_conserva_fuera_del_informe_incluso_al_reintentar(self):
        inicializar(self.db)
        folio = self.emitir()
        for motivo in ("Motivo ficticio A", "Motivo ficticio B"):
            with self.db:
                recibo = operaciones(self.db, "admin", "cancelar", {"factura": folio, "motivo": motivo})
                self.assertEqual(recibo["estado"], "cancelada")
                self.assertNotIn("motivo", recibo)
        for usuario in ("auditor", "admin"):
            informe = operaciones(self.db, usuario, "auditoria", {})
            cancelaciones = [evento for evento in informe if evento["accion"] == "cancelación"]
            self.assertEqual(len(cancelaciones), 1)
            self.assertEqual(cancelaciones[0]["detalle"], "")
            self.assertEqual(cancelaciones[0]["entidad"], str(folio))
            self.assertEqual(cancelaciones[0]["usuario"], "admin")
        expediente = self.db.execute("""SELECT a.detalle,m.motivo,a.entidad
            FROM motivos_cancelacion m JOIN auditoria a ON a.id=m.evento""").fetchall()
        self.assertEqual([tuple(fila) for fila in expediente], [("", "Motivo ficticio A", str(folio))])

    def test_migra_eventos_antiguos_sin_perder_su_fecha_ni_el_texto_original(self):
        self.db.execute("""CREATE TABLE auditoria(id INTEGER PRIMARY KEY,fecha TEXT,usuario TEXT,
            accion TEXT,entidad TEXT,detalle TEXT)""")
        self.db.execute("INSERT INTO auditoria VALUES(17,'2002-04-01','admin','cancelación','5','Motivo antiguo')")
        self.db.execute("INSERT INTO auditoria VALUES(18,'2002-04-01','admin','tarifa','2','100 a 105')")
        self.db.commit()
        inicializar(self.db)
        inicializar(self.db)
        filas = self.db.execute("SELECT id,fecha,detalle FROM auditoria ORDER BY id").fetchall()
        self.assertEqual([tuple(f) for f in filas], [(17,"2002-04-01",""), (18,"2002-04-01","100 a 105")])
        motivos = self.db.execute("SELECT evento,motivo FROM motivos_cancelacion").fetchall()
        self.assertEqual([tuple(f) for f in motivos], [(17,"Motivo antiguo")])

    def test_fallo_antes_de_confirmar_revierte_expediente_evento_y_factura(self):
        inicializar(self.db)
        folio = self.emitir()
        with self.assertRaises(RuntimeError):
            with self.db:
                operaciones(self.db, "admin", "cancelar", {"factura": folio, "motivo": "Motivo ficticio"})
                raise RuntimeError("Interrupción ficticia")
        recibo = operaciones(self.db, "operador", "comprobante", {"factura": folio})
        self.assertEqual(recibo["estado"], "emitida")
        self.assertEqual(self.db.execute("SELECT count(*) FROM motivos_cancelacion").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM auditoria WHERE accion='cancelación'").fetchone()[0], 0)
