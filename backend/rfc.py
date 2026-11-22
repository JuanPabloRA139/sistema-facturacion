"""Revisión preliminar del RFC que recibirá la API de clientes."""
import re
from datetime import date

FORMATO = re.compile(r"[A-ZÑ&]{3,4}([0-9]{2})([0-9]{2})([0-9]{2})[A-Z0-9]{2}[0-9A]")

def formato_rfc_valido(valor):
    if not isinstance(valor, str):
        return False
    partes = FORMATO.fullmatch(valor.strip().upper())
    if partes is None:
        return False
    anio, mes, dia = map(int, partes.groups())
    try:
        date(2000 + anio, mes, dia)
    except ValueError:
        return False
    return True
