"""Revisión preliminar del RFC que recibirá la API de clientes."""
import re
from datetime import date

FORMATO = re.compile(r"[A-ZÑ&]{3,4}([0-9]{2})([0-9]{2})([0-9]{2})[A-Z0-9]{2}[0-9A]")

def validar_rfc(valor):
    rfc = valor.strip().upper() if isinstance(valor, str) else ""
    partes = FORMATO.fullmatch(rfc)
    if partes is None:
        raise ValueError("Revisa el formato del RFC: escribe las letras iniciales, la fecha y los tres caracteres finales.")
    anio, mes, dia = map(int, partes.groups())
    try:
        date(2000 + anio, mes, dia)
    except ValueError as exc:
        raise ValueError("Revisa la fecha del RFC: el mes y el día deben formar una fecha válida.") from exc
    return rfc


def formato_rfc_valido(valor):
    try:
        validar_rfc(valor)
    except ValueError:
        return False
    return True
