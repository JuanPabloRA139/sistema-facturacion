"""Punto de entrada Lambda para la ruta POST /api/{accion} de HTTP API v2."""
import base64
import json
from contextlib import closing
from datetime import date
from backend.rds import conectar, FacturacionPostgres, preparar_actor
from backend.identidades import rol_de
from backend.entrada import leer_objeto
from backend.servicios import TotalModificado, ejecutar


def serializar(valor):
    if isinstance(valor, date):
        return valor.isoformat()
    raise TypeError("Tipo de respuesta no admitido.")


def respuesta(codigo, datos):
    return {"statusCode": codigo, "headers": {"Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            "body": json.dumps(datos, ensure_ascii=False, default=serializar)}


def handler(event, context):
    request = event.get("requestContext", {})
    claims = request.get("authorizer", {}).get("jwt", {}).get("claims", {})
    usuario = claims.get("sub")
    if not usuario or claims.get("token_use") != "access":
        return respuesta(401, {"error": "Inicia sesión."})
    if request.get("http", {}).get("method") != "POST":
        return respuesta(405, {"error": "Método no disponible."})
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
        return respuesta(415, {"error": "Se requiere JSON."})
    cuerpo = event.get("body") or ""
    if len(cuerpo) > 45000:
        return respuesta(413, {"error": "Solicitud demasiado grande."})
    try:
        raw = base64.b64decode(cuerpo, validate=True) if event.get("isBase64Encoded") else cuerpo.encode()
        if len(raw) > 32768:
            return respuesta(413, {"error": "Solicitud demasiado grande."})
        datos = leer_objeto(raw)
    except (TypeError, ValueError):
        return respuesta(400, {"error": "Se requiere un objeto JSON."})
    accion = (event.get("pathParameters") or {}).get("accion")
    try:
        with closing(conectar()) as db:
            with closing(db.cursor()) as cursor:
                from backend.auditoria_aws import recientes
                rol = preparar_actor(cursor, usuario, rol_de)
                repo = FacturacionPostgres(cursor, usuario, rol, recientes)
                salida = ejecutar(repo, rol, accion, datos)
                resultado = respuesta(200, salida)
            db.commit()
            if accion in {"emitir","pago","cancelar","tarifa","auditoria"}:
                from backend.auditoria_aws import exportar, recientes
                try:
                    exportar(db)
                    if accion == "auditoria":
                        resultado = respuesta(200, recientes())
                except Exception:
                    print("Auditoría pendiente", getattr(context,"aws_request_id",""))
        return resultado
    except TotalModificado as exc:
        return respuesta(409, {"error": str(exc)})
    except PermissionError:
        return respuesta(403, {"error": "Acceso denegado."})
    except ValueError:
        return respuesta(400, {"error": "Revisa los datos de la operación."})
    except Exception as error:
        # pg8000 incluye el SQLSTATE en la clave C. Los detalles internos no salen en la respuesta.
        diagnostico = error.args[0] if error.args and isinstance(error.args[0], dict) else {}
        codigo = diagnostico.get("C", "")
        if codigo == "P0002":
            return respuesta(404, {"error": "Registro no disponible."})
        if codigo.startswith("23") or codigo == "P0001":
            return respuesta(409, {"error": "La operación entra en conflicto con los datos actuales."})
        print("Error de servicio", getattr(context, "aws_request_id", ""), type(error).__name__)
        return respuesta(503, {"error": "Servicio temporalmente no disponible."})
