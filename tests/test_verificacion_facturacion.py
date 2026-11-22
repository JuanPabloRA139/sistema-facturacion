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
