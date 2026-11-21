"""Casos de uso del panel. Reciben un repositorio y no dependen de AWS ni de SQL."""
from datetime import date
import re
import unicodedata

from backend.rfc import formato_rfc_valido


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
    rfc = cadena(datos.get("rfc"), 13).upper()
    if not formato_rfc_valido(rfc):
        raise ValueError("Formato de RFC incompatible.")
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


def tarifa(repo, datos):
    servicio = entero(datos.get("servicio"))
    precio = entero(datos.get("precio"), 10000000)
    repo.cambiar_tarifa(servicio, precio)
    return {"servicio": servicio, "precio": precio}


def asignar(repo, datos):
    servicios = lista_ids(datos.get("servicios"), 100)
    caracteristicas = lista_ids(datos.get("caracteristicas"), 50)
    repo.asignar(servicios, caracteristicas)
    return {"asignaciones_solicitadas": len(servicios) * len(caracteristicas)}


def saldos(repo, datos):
    return repo.saldos()


def cierre(repo, datos):
    periodo = cadena(datos.get("periodo"), 10)
    if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", periodo):
        raise ValueError("Usa AAAA-MM o AAAA-MM-DD.")
    mensual = len(periodo) == 7
    fecha = date.fromisoformat(periodo + "-01" if mensual else periodo)
    hoy = date.today()
    if fecha >= hoy or (mensual and fecha.replace(day=1) >= hoy.replace(day=1)):
        raise ValueError("El periodo debe haber terminado.")
    return {"periodo": periodo, "neto": repo.cerrar(fecha, mensual)}


def auditoria(repo, datos):
    return repo.auditoria()


TODOS = {"administrador", "operador", "auditor"}
ESCRITURA = {"administrador", "operador"}
ADMIN = {"administrador"}
OPERACIONES = {
    "inicio": (inicio, TODOS), "cliente": (cliente, ESCRITURA),
    "emitir": (emitir, ESCRITURA), "comprobante": (comprobante, TODOS),
    "pago": (pago, ESCRITURA), "cancelar": (cancelar, ADMIN),
    "tarifa": (tarifa, ADMIN), "asignar": (asignar, ADMIN),
    "saldos": (saldos, TODOS), "cierre": (cierre, ADMIN),
    "auditoria": (auditoria, {"administrador", "auditor"}),
}


CAMPOS = {
    "inicio": (), "cliente": ("nombre", "rfc"), "emitir": ("clave", "cliente", "conceptos", "total_esperado"),
    "comprobante": ("factura",), "pago": ("factura", "referencia", "importe"),
    "cancelar": ("factura", "motivo"), "tarifa": ("servicio", "precio"),
    "asignar": ("servicios", "caracteristicas"), "saldos": (), "cierre": ("periodo",), "auditoria": (),
}


def ejecutar(repo, rol, accion, datos):
    if accion not in OPERACIONES:
        raise ValueError("Operación desconocida.")
    operacion, permisos = OPERACIONES[accion]
    if rol not in permisos:
        raise PermissionError
    if not isinstance(datos, dict) or datos.keys() - CAMPOS[accion]:
        raise ValueError("La solicitud contiene campos no admitidos.")
    return operacion(repo, datos)
