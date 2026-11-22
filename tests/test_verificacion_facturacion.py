"""Pruebas funcionales sobre los servicios de facturación y la base local."""
import unittest

from backend.local import conectar, inicializar, operaciones


class VerificacionFacturacion(unittest.TestCase):
    def setUp(self):
        self.db = conectar(":memory:")
        self.addCleanup(self.db.close)
        inicializar(self.db)
        cliente = self.operar("inicio")["clientes"][0]["id"]
        self.solicitud = {
            "cliente": cliente,
            "clave": "demo-facturacion",
            "conceptos": [{"servicio": 1, "cantidad": 1}],
        }
        self.factura = self.operar("emitir", **self.solicitud)
        self.folio = self.factura["id"]

    def operar(self, accion, usuario="operador", **datos):
        with self.db:
            return operaciones(self.db, usuario, accion, datos)

    def pagar(self, importe, referencia="PAGO-01", usuario="operador"):
        return self.operar("pago", usuario, factura=self.folio,
                           referencia=referencia, importe=importe)

    def test_desglose_de_la_emision(self):
        recibido = self.operar("comprobante", factura=self.folio)
        esperado = {"subtotal": 10500, "iva": 1680, "retencion": 420,
                    "total": 11760, "pagado": 0, "saldo": 11760, "estado": "emitida"}
        self.assertEqual({campo: recibido[campo] for campo in esperado}, esperado)

    def test_reintento_de_emision_conserva_detalle_y_movimiento(self):
        repetida = self.operar("emitir", **self.solicitud)
        self.assertEqual(repetida["id"], self.folio)
        self.assertEqual(len(repetida["conceptos"]), 1)
        movimientos = self.db.execute(
            "SELECT concepto, importe FROM movimientos WHERE factura = ?", (self.folio,)
        ).fetchall()
        self.assertEqual([tuple(fila) for fila in movimientos], [("emision", 11760)])

    def test_reintento_respeta_el_precio_historico(self):
        self.operar("tarifa", "admin", servicio=1, precio=20000)
        repetida = self.operar("emitir", **self.solicitud)
        nueva = self.operar("emitir", **{**self.solicitud, "clave": "nueva-tarifa"})
        self.assertEqual((repetida["id"], repetida["total"]), (self.folio, 11760))
        self.assertEqual(nueva["total"], 22400)

    def test_pago_parcial_coincide_con_cartera(self):
        self.pagar(5000)
        recibo = self.operar("comprobante", factura=self.folio)
        cartera = {f["folio"]: f["saldo"] for f in self.operar("saldos")}
        self.assertEqual((recibo["estado"], recibo["pagado"], recibo["saldo"]),
                         ("parcial", 5000, 6760))
        self.assertEqual(cartera[self.folio], recibo["saldo"])

    def test_reintento_de_pago_se_registra_una_vez(self):
        primero = self.pagar(5000)
        segundo = self.pagar(5000)
        self.assertFalse(primero["pago_duplicado"])
        self.assertTrue(segundo["pago_duplicado"])
        self.assertEqual(segundo["saldo"], 6760)
        cobros = self.db.execute(
            "SELECT count(*), sum(importe) FROM pagos WHERE factura = ?", (self.folio,)
        ).fetchone()
        self.assertEqual(tuple(cobros), (1, 5000))
        eventos = self.db.execute(
            "SELECT count(*) FROM auditoria WHERE accion = 'pago' AND entidad = ?",
            (str(self.folio),)
        ).fetchone()[0]
        self.assertEqual(eventos, 1)

    def test_referencia_con_otro_importe_conserva_el_pago_original(self):
        self.pagar(5000)
        with self.assertRaises(ValueError):
            self.pagar(5001)
        recibo = self.operar("comprobante", factura=self.folio)
        self.assertEqual((recibo["pagado"], recibo["saldo"]), (5000, 6760))
        fila = self.db.execute(
            "SELECT importe FROM pagos WHERE factura = ? AND referencia = ?",
            (self.folio, "PAGO-01")
        ).fetchone()
        self.assertEqual(fila[0], 5000)

    def test_liquidar_y_reintentar_el_ultimo_centavo(self):
        self.pagar(11759, "ANTICIPO")
        self.assertEqual(self.pagar(1, "FINAL")["estado"], "pagada")
        repetido = self.pagar(1, "FINAL")
        self.assertTrue(repetido["pago_duplicado"])
        self.assertEqual((repetido["pagado"], repetido["saldo"]), (11760, 0))
        self.assertNotIn(self.folio, [f["folio"] for f in self.operar("saldos")])

    def test_segundo_operador_no_consulta_ni_cobra_el_folio(self):
        resumen = self.operar("inicio", "operador2")
        self.assertNotIn(self.folio, [f["id"] for f in resumen["facturas"]])
        with self.assertRaises(ValueError):
            self.operar("comprobante", "operador2", factura=self.folio)
        with self.assertRaises(ValueError):
            self.pagar(5000, usuario="operador2")
        self.assertEqual(self.operar("comprobante", factura=self.folio)["saldo"], 11760)

    def test_auditor_consulta_el_saldo_pero_no_lo_modifica(self):
        self.pagar(5000)
        with self.assertRaises(PermissionError):
            self.pagar(100, "INTENTO", "auditor")
        lectura = self.operar("comprobante", "auditor", factura=self.folio)
        self.assertEqual((lectura["pagado"], lectura["saldo"]), (5000, 6760))

    def test_cancelacion_repetida_compensa_solo_una_emision(self):
        for _ in range(2):
            recibo = self.operar("cancelar", "admin", factura=self.folio, motivo="Prueba")
            self.assertEqual((recibo["estado"], recibo["saldo"]), ("cancelada", 0))
        movimientos = self.db.execute(
            "SELECT concepto, importe FROM movimientos WHERE factura = ? ORDER BY id",
            (self.folio,)
        ).fetchall()
        self.assertEqual([tuple(fila) for fila in movimientos],
                         [("emision", 11760), ("reversion", -11760)])
