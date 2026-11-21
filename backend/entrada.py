"""Lectura estricta de los objetos JSON enviados por el panel."""
import json


def pares_unicos(pares):
    objeto = dict(pares)
    if len(objeto) != len(pares):
        raise ValueError("Campos repetidos.")
    return objeto


def numero_invalido(_):
    raise ValueError("Se requieren importes y cantidades enteras.")


def leer_objeto(raw):
    try:
        valor = json.loads(raw.decode("utf-8"), object_pairs_hook=pares_unicos,
                           parse_float=numero_invalido, parse_constant=numero_invalido)
    except (ValueError, RecursionError) as exc:
        raise ValueError("JSON inválido o ambiguo.") from exc
    if not isinstance(valor, dict):
        raise ValueError("Se requiere un objeto JSON.")
    return valor
