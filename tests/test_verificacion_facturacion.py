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
