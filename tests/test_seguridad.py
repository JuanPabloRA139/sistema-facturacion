import os
import re
from html.parser import HTMLParser
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from backend.api_aws import handler as api
from backend.entrada import leer_objeto
from backend.servicios import ejecutar
from backend.web_aws import handler as web


class SeguridadTest(unittest.TestCase):
    def test_json_ambiguo_o_malformado(self):
        for raw in (b'[]', b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1.23}', b'{"x":"\xff"}', b'['*1300+b']'*1300):
            with self.subTest(raw=raw[:20]), self.assertRaises(ValueError):
                leer_objeto(raw)

    def test_campos_y_limites(self):
        for accion, campos in (
            ("inicio", {"rol": "administrador"}),
            ("emitir", {"clave":"a","cliente":True,"conceptos":[]}),
            ("emitir", {"clave":"a","cliente":1,"conceptos":[{"servicio":1,"cantidad":1,"precio":1}]}),
            ("emitir", {"clave":"a","cliente":1,"conceptos":[{"servicio":1,"cantidad":1000}]}),
            ("asignar", {"servicios":[1,1],"caracteristicas":[2]}),
            ("cliente", {"nombre":"A\u202eB","rfc":"ZETA000229AB1"}),
            ("pago", {"factura":1,"referencia":"A\u0000B","importe":1}),
            ("cierre", {"periodo":"9999-12"}),
        ):
            repo = Mock()
            with self.subTest(accion=accion), self.assertRaises(ValueError):
                ejecutar(repo, "administrador", accion, campos)
            self.assertFalse(repo.mock_calls)

