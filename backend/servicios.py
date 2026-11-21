"""Casos de uso del panel. Reciben un repositorio y no dependen de AWS ni de SQL."""
from datetime import date
import re
import unicodedata

from backend.rfc import validar_rfc


class TotalModificado(ValueError):
    pass


def entero(valor, maximo=10**9):
    if type(valor) is not int or not 1 <= valor <= maximo:
        raise ValueError("Número fuera de rango.")
    return valor


def cadena(valor, maximo):
    if not isinstance(valor, str) or not 1 <= len(valor.strip()) <= maximo:
        raise ValueError("Texto vacío o demasiado largo.")
    if any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in valor):
        raise ValueError("El texto contiene caracteres de control.")
    return valor.strip()


def lista_ids(valores, limite):
    if not isinstance(valores, list) or not 1 <= len(valores) <= limite:
        raise ValueError("Selecciona una lista válida.")
    ids = [entero(valor) for valor in valores]
    if len(set(ids)) != len(ids):
        raise ValueError("Hay elementos repetidos en la selección.")
    return ids


def inicio(repo, datos):
    return repo.inicio()


def cliente(repo, datos):
    nombre = cadena(datos.get("nombre"), 100)
    rfc = validar_rfc(cadena(datos.get("rfc"), 13))
    return {"cliente": repo.crear_cliente(nombre, rfc)}


def emitir(repo, datos):
    clave = cadena(datos.get("clave"), 80)
    cliente_id = entero(datos.get("cliente"))
    lineas = datos.get("conceptos")
    if not isinstance(lineas, list) or not 1 <= len(lineas) <= 30:
        raise ValueError("Agrega de 1 a 30 conceptos.")
    conceptos = []
    for linea in lineas:
        if not isinstance(linea, dict) or set(linea) != {"servicio", "cantidad"}:
            raise ValueError("Concepto inválido.")
        conceptos.append({"servicio": entero(linea.get("servicio")), "cantidad": entero(linea.get("cantidad"), 999)})
    esperado = datos.get("total_esperado")
    if "total_esperado" in datos and (type(esperado) is not int or not 0 <= esperado <= 10**13):
        raise ValueError("Total esperado inválido.")
    factura = repo.comprobante(repo.emitir(cliente_id, clave, conceptos))
    if esperado is not None and factura["total"] != esperado:
        # Ambos adaptadores conservan la transacción abierta hasta que termina este caso de uso.
        raise TotalModificado("El total cambió. Revisa el resumen y confirma nuevamente.")
    return factura


def comprobante(repo, datos):
    return repo.comprobante(entero(datos.get("factura")))


def pago(repo, datos):
    folio = entero(datos.get("factura"))
    referencia = cadena(datos.get("referencia"), 64)
    duplicado = repo.registrar_pago(folio, referencia, entero(datos.get("importe")))
    return dict(repo.comprobante(folio), pago_duplicado=duplicado)


def cancelar(repo, datos):
    folio = entero(datos.get("factura"))
    repo.cancelar(folio, cadena(datos.get("motivo"), 160))
    return repo.comprobante(folio)


