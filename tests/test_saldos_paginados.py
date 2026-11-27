import json
import unittest
from datetime import date, timedelta
from unittest.mock import Mock
from uuid import uuid4

from backend.local import conectar, inicializar, operaciones
from backend.rds import FacturacionPostgres
from backend.servicios import ejecutar


class SaldosPaginados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = conectar(":memory:")
        inicializar(cls.db)
        cls.addClassCleanup(cls.db.close)
        for usuario, cantidad in (("operador", 201), ("operador2", 1)):
            cliente = operaciones(cls.db, usuario, "inicio", {})["clientes"][0]["id"]
            for _ in range(cantidad):
                factura = operaciones(cls.db, usuario, "emitir", {
                    "clave": str(uuid4()), "cliente": cliente,
                    "conceptos": [{"servicio": 1, "cantidad": 1}]})
                ultimo = factura["id"]
            if usuario == "operador2":
                cls.ajeno = ultimo
        operaciones(cls.db, "operador", "pago", {"factura": 1, "referencia": "PARCIAL", "importe": 5000})
        # El folio más nuevo vence primero; muchos registros comparten vencimiento.
        cls.db.execute("UPDATE facturas SET vence=? WHERE id=201", (str(date.today()-timedelta(days=8)),))
        cls.db.commit()

    def consultar(self, usuario="operador", **opciones):
        return operaciones(self.db, usuario, "saldos", opciones)

    def test_recorrido_completo_pagos_parciales_y_legado(self):
        uno = self.consultar(paginado=True)
        dos = self.consultar(paginado=True, despues_de=uno["siguiente"])
        filas = uno["filas"] + dos["filas"]
        self.assertEqual([len(uno["filas"]), len(dos["filas"])], [200, 1])
        self.assertEqual(uno["filas"][0]["folio"], 201)
        self.assertEqual(uno["filas"][0]["dias_vencidos"], 8)
        self.assertIsNone(dos["siguiente"])
        self.assertEqual({f["folio"] for f in filas}, set(range(1, 202)))
        self.assertEqual(sum(f["saldo"] for f in filas), 201*11760-5000)
        self.assertEqual(self.consultar(), uno["filas"])
        vacia = self.consultar(paginado=True, despues_de={"vence": "9999-12-31", "folio": 1})
        self.assertEqual(vacia, {"filas": [], "siguiente": None})

    def test_aislamiento_y_lectura_auditor(self):
        ajeno = self.consultar("operador2", paginado=True)
        self.assertEqual([f["folio"] for f in ajeno["filas"]], [self.ajeno])
        self.assertIsNone(ajeno["siguiente"])
        cursor_otro = self.consultar(paginado=True)["siguiente"]
        desde_otro = self.consultar("operador2", paginado=True, despues_de=cursor_otro)
        self.assertEqual(desde_otro, ajeno)
        pagina = self.consultar("auditor", paginado=True)
        resto = self.consultar("auditor", paginado=True, despues_de=pagina["siguiente"])
        self.assertIn(self.ajeno, [f["folio"] for f in resto["filas"]])

    def test_200_exactas_y_omision_de_factura_liquidada(self):
        self.db.execute("SAVEPOINT pago_temporal")
        try:
            operaciones(self.db, "operador", "pago", {"factura": 1, "referencia": "SALDO", "importe": 6760})
            pagina = self.consultar(paginado=True)
            self.assertEqual(len(pagina["filas"]), 200)
            self.assertIsNone(pagina["siguiente"])
            self.assertNotIn(1, [f["folio"] for f in pagina["filas"]])
        finally:
            self.db.execute("ROLLBACK TO pago_temporal")
            self.db.execute("RELEASE pago_temporal")

    def test_cursor_invalido_se_rechaza_antes_del_repositorio(self):
        repo = Mock()
        for datos in ({"paginado": False}, {"despues_de": {}}, {"paginado": 1},
                      {"paginado": True, "despues_de": None},
                      {"paginado": True, "despues_de": {"vence": "2026-02-30", "folio": 1}},
                      {"paginado": True, "despues_de": {"vence": "2026-02-01", "folio": True}},
                      {"paginado": True, "despues_de": {"vence": "2026-02-01", "folio": 0, "otro": 1}}):
            with self.subTest(datos=datos), self.assertRaises(ValueError):
                ejecutar(repo, "operador", "saldos", datos)
        repo.saldos.assert_not_called()

    def test_adaptador_pg_convierte_tambien_el_importe_de_la_ultima_pagina(self):
        cur = Mock()
        repo = FacturacionPostgres(cur, "u", "operador", None)
        cur.fetchone.return_value = ('[{"folio":201,"vence":"2026-12-31","saldo":67.60}]',)
        cursor = {"vence": "2026-12-31", "folio": 200}
        pagina = ejecutar(repo, "operador", "saldos", {"paginado": True, "despues_de": cursor})
        self.assertEqual(pagina["filas"][0]["saldo"], 6760)
        self.assertIsNone(pagina["siguiente"])
        self.assertEqual(pagina["filas"][0]["folio"], 201)
        argumentos = cur.execute.call_args.args[1]
        self.assertEqual(argumentos[0], "u")
        self.assertEqual(json.loads(argumentos[1]), {"paginado": True, "despues_de": cursor})
