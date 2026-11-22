"""Exportación por lotes. Un reintento reutiliza la identidad del evento."""
import json
import os
from contextlib import closing
from datetime import timezone
import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from backend.rds import conectar

def tabla():
    return boto3.resource("dynamodb").Table(os.environ["AUDIT_TABLE"])

def exportar(db):
    destino = tabla()
    with closing(db.cursor()) as cur:
        cur.execute("""SELECT evento_id,fecha,entidad,accion,actor,detalle FROM eventos_pendientes
                       WHERE NOT enviado ORDER BY evento_id LIMIT 20 FOR UPDATE SKIP LOCKED""")
        registros = cur.fetchall()
        for numero,fecha,entidad,accion,actor,detalle in registros:
            instante = fecha.astimezone(timezone.utc).isoformat(timespec="microseconds")
            clave = f"{instante}#{numero:020d}"
            item = dict(entidad=entidad, evento=clave, listado="recientes", fecha=instante,
                        accion=accion, usuario=actor, detalle=json.loads(detalle) if isinstance(detalle,str) else detalle)
            try:
                destino.put_item(Item=item, ConditionExpression="attribute_not_exists(evento)")
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
            cur.execute("UPDATE eventos_pendientes SET enviado=true WHERE evento_id=%s",(numero,))
    db.commit()
    return len(registros)

def recientes():
    items = tabla().query(IndexName="historial",KeyConditionExpression=Key("listado").eq("recientes"),
                          ScanIndexForward=False,Limit=100).get("Items", [])
    return [dict(fecha=i["fecha"],usuario=i["usuario"],accion=i["accion"],entidad=i["entidad"],
                 detalle=" · ".join(f"{k} {v}" for k,v in i["detalle"].items())) for i in items]

def handler(event, context):
    with closing(conectar()) as db:
        return {"enviados":exportar(db)}
