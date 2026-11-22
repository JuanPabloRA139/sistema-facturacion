import unittest
from backend.rfc import formato_rfc_valido

class FormatoRfcTest(unittest.TestCase):
    def test_fecha_y_formato(self):
        for entrada, esperado in [
            ("ZETA000229AB1", True), (" zzz991231aa0 ", True),
            ("ZETA010229AB1", False), ("ZETA991301AB1", False),
            ("ZETA991200AB1", False), ("ZETA000229ABZ", False),
            ("ZZ000229AB1", False), ("", False), (None, False),
        ]:
            with self.subTest(entrada=entrada):
                self.assertEqual(formato_rfc_valido(entrada), esperado)
