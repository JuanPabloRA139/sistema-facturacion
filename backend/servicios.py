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


