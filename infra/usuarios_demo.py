"""Prepara usuarios sintéticos en la cuenta AWS Academy, sin enviar invitaciones."""
import json
import secrets
import string
import boto3
from botocore.exceptions import ClientError

cf=boto3.client("cloudformation")
stack=cf.describe_stacks(StackName="facturacion-servicios-lab")["Stacks"][0]
out={i["OutputKey"]:i["OutputValue"] for i in stack["Outputs"]}
secm=boto3.client("secretsmanager")
idp=boto3.client("cognito-idp")
fn=boto3.client("lambda")
nombre="facturacion-servicios-lab/accesos-demo"
roles={"admin-demo":"administrador","operador-demo":"operador","auditor-demo":"auditor","operador-dos":"operador"}
try:
    claves=json.loads(secm.get_secret_value(SecretId=nombre)["SecretString"])
except secm.exceptions.ResourceNotFoundException:
    claves={u:"".join(secrets.SystemRandom().sample("Aa9!"+secrets.token_urlsafe(28),32))+"aB7!" for u in roles}
    secm.create_secret(Name=nombre,SecretString=json.dumps(claves),Tags=[{"Key":"Proyecto","Value":"FacturacionServicios"}])
for usuario,rol in roles.items():
    try:
        idp.admin_get_user(UserPoolId=out["UserPool"],Username=usuario)
    except idp.exceptions.UserNotFoundException:
        idp.admin_create_user(UserPoolId=out["UserPool"],Username=usuario,MessageAction="SUPPRESS")
    idp.admin_set_user_password(UserPoolId=out["UserPool"],Username=usuario,Password=claves[usuario],Permanent=True)
    attrs=idp.admin_get_user(UserPoolId=out["UserPool"],Username=usuario)["UserAttributes"]
    sub=next(a["Value"] for a in attrs if a["Name"]=="sub")
    inv=fn.invoke(FunctionName=out["AdminFunction"],Payload=json.dumps({"accion":"autorizar","sub":sub,"rol":rol}).encode())
    if inv.get("FunctionError"): raise RuntimeError("No se asignó el rol de "+usuario)
print("Accesos demo listos. Sus claves están en el secreto "+nombre)
