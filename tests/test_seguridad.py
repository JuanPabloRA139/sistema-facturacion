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

    @patch.dict(os.environ, {"LOGIN_DOMAIN":"https://login.example", "CLIENT_ID":"cliente"})
    def test_web_aws_acceso_y_archivos(self):
        pagina = web({"rawPath":"/"}, None)
        self.assertIn('id="confirmacion"', pagina["body"])
        self.assertIn('id="login-aws"', pagina["body"])
        self.assertNotIn('id="login"', pagina["body"])
        self.assertNotIn("demo", pagina["body"].lower())
        self.assertIn("frame-ancestors 'none'", pagina["headers"]["Content-Security-Policy"])
        self.assertNotIn("unsafe-inline", pagina["headers"]["Content-Security-Policy"])
        self.assertEqual(web({"rawPath":"/backend/servicios.py"}, None)["statusCode"],404)
        for ruta in ("panel.js","panel.css","rfc.js","acceso-aws.js","config-publica"):
            self.assertEqual(web({"rawPath":"/"+ruta}, None)["statusCode"],200)

    @patch("backend.api_aws.conectar")
    def test_api_rechaza_antes_de_abrir_bd(self, conectar):
        evento = {"requestContext":{"authorizer":{"jwt":{"claims":{"sub":"usuario","token_use":"access"}}},
                                    "http":{"method":"POST"}}, "headers":{"Content-Type":"application/json"}}
        for cambios,codigo in (({"requestContext":{}},401),({"headers":{}},415),({"body":"[]"},400),
                               ({"body":"a"*45001},413),({"body":"{}","isBase64Encoded":True},400)):
            self.assertEqual(api({**evento,**cambios},None)["statusCode"],codigo)
        evento["body"] = "{}"
        self.assertEqual(api({**evento, "pathParameters": {"accion": "desconocida"}}, None)["statusCode"], 400)
        self.assertEqual(api({**evento, "body": '{"extra":true}', "pathParameters": {"accion": "inicio"}}, None)["statusCode"], 400)
        conectar.assert_not_called()


    @patch.dict(os.environ, {"LOGIN_DOMAIN":"https://login.example", "CLIENT_ID":"cliente"})
    def test_plantillas_y_puntos_de_salida_del_panel(self):
        class Inventario(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = []
                self.eventos = []
            def handle_starttag(self, tag, attrs):
                for k, v in attrs:
                    if k == "id":
                        self.ids.append(v)
                    if k.startswith("on"):
                        self.eventos.append(k)

        frontend = Path(__file__).resolve().parents[1] / "frontend"
        fuente = (frontend / "panel.js").read_text(encoding="utf-8")
        for pagina, opcional in (((frontend/"panel.html").read_text(encoding="utf-8"), "login-aws"),
                                 (web({"rawPath":"/"}, None)["body"], "login")):
            inventario = Inventario()
            inventario.feed(pagina)
            self.assertFalse(inventario.eventos)
            self.assertEqual(len(inventario.ids), len(set(inventario.ids)))
            referencias = set(re.findall(r"\bel\('([^']+)'\)", fuente))
            self.assertFalse(referencias - set(inventario.ids) - {opcional})
        for js in frontend.glob("*.js"):
            texto = js.read_text(encoding="utf-8")
            for salida in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write(", "eval(", "new Function("):
                self.assertNotIn(salida, texto)
