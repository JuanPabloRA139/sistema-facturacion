import unittest
from unittest.mock import Mock

from backend.rds import preparar_actor
from backend.servicios import OPERACIONES, ejecutar


class ServiciosTest(unittest.TestCase):
    def test_pago_duplicado_preserva_saldo(self):
        repo = Mock()
        repo.registrar_pago.return_value = True
        repo.comprobante.return_value = {"saldo": 6760}
        resultado = ejecutar(repo, "operador", "pago", {"factura": 1, "referencia": "DEMO-1", "importe": 5000})
        self.assertEqual(resultado, {"saldo": 6760, "pago_duplicado": True})
        repo.registrar_pago.assert_called_once_with(1, "DEMO-1", 5000)

    def test_roles_sin_permiso_no_llaman_al_repositorio(self):
        for accion, (_, permitidos) in OPERACIONES.items():
            for rol in {"administrador", "operador", "auditor", "desconocido"} - permitidos:
                with self.subTest(accion=accion, rol=rol):
                    repo = Mock()
                    with self.assertRaises(PermissionError):
                        ejecutar(repo, rol, accion, {})
                    self.assertFalse(repo.mock_calls)

    def test_directorio_obligatorio_y_consistente(self):
        for copia in (None, ("administrador",)):
            cur = Mock()
            cur.fetchone.return_value = copia
            with self.assertRaises(PermissionError):
                preparar_actor(cur, "cuenta", lambda usuario: "operador")
        cur = Mock()
        with self.assertRaises(ConnectionError):
            preparar_actor(cur, "cuenta", Mock(side_effect=ConnectionError))
        cur.fetchone.assert_not_called()

    def test_actor_valido(self):
        cur = Mock()
        cur.fetchone.return_value = ("auditor",)
        resolver = Mock(return_value="auditor")
        self.assertEqual(preparar_actor(cur, "cuenta", resolver), "auditor")
        resolver.assert_called_once_with("cuenta")

    def test_rfc_invalido_no_se_persiste(self):
        repo = Mock()
        with self.assertRaises(ValueError):
            ejecutar(repo, "operador", "cliente", {"nombre": "Ejemplo", "rfc": "ABC991332AB1"})
        repo.crear_cliente.assert_not_called()
