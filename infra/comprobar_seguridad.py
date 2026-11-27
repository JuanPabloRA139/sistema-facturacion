"""Inventario de solo lectura para CloudShell. Los resultados omiten IDs y secretos."""
import sys

PILA = "facturacion-servicios-lab"
REGION = "us-east-1"


def ingreso_postgres(reglas, grupo_app):
    """Todas las reglas entrantes deben apuntar al mismo grupo y puerto."""
    return bool(reglas) and all(
        r.get("IpProtocol") == "tcp" and r.get("FromPort") == r.get("ToPort") == 5432
        and not any(r.get(k) for k in ("IpRanges", "Ipv6Ranges", "PrefixListIds"))
        and {par["GroupId"] for par in r.get("UserIdGroupPairs", [])} == {grupo_app}
        for r in reglas
    )


def listar(operacion, campo, *, marcador="NextToken", siguiente="NextToken", **parametros):
    elementos = []
    while True:
        pagina = operacion(**parametros)
        elementos.extend(pagina.get(campo, []))
        if not pagina.get(siguiente):
            return elementos
        parametros[marcador] = pagina[siguiente]


def main():
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    sesion = boto3.Session(region_name=REGION)
    cf = sesion.client("cloudformation")
    pendientes = []
    diferencias = []

    def comprobar(nombre, consulta):
        try:
            coincide = consulta()
        except ClientError as error:
            codigo = error.response["Error"]["Code"]
            print(f"PENDIENTE | {nombre} | AWS: {codigo}")
            pendientes.append(nombre)
        except (BotoCoreError, KeyError, IndexError) as error:
            print(f"PENDIENTE | {nombre} | {type(error).__name__}")
            pendientes.append(nombre)
        else:
            print(("VERIFICADO" if coincide else "REVISAR") + " | " + nombre)
            if not coincide:
                diferencias.append(nombre)

    ids = {}

    def recursos():
        paginas = cf.get_paginator("list_stack_resources").paginate(StackName=PILA)
        for pagina in paginas:
            for recurso in pagina["StackResourceSummaries"]:
                ids[recurso["LogicalResourceId"]] = recurso["PhysicalResourceId"]
        return {"Database", "IdentityDatabase", "Http", "Web", "Api", "Admin", "Audit",
                "DBGroup", "AppGroup", "Authorizer", "Users", "Client"} <= ids.keys()

    comprobar("CloudFormation alcanzó un estado completo",
              lambda: cf.describe_stacks(StackName=PILA)["Stacks"][0]["StackStatus"]
              in {"CREATE_COMPLETE", "UPDATE_COMPLETE"})
    comprobar("Recursos esperados en la pila", recursos)
    if not ids:
        return 2

    rds = sesion.client("rds")

    def base_correcta(nombre):
        db = rds.describe_db_instances(DBInstanceIdentifier=ids[nombre])["DBInstances"][0]
        return (db["Engine"] == "postgres" and db["PubliclyAccessible"] is False
                and db["StorageEncrypted"] and db["BackupRetentionPeriod"] >= 1
                and {g["VpcSecurityGroupId"] for g in db["VpcSecurityGroups"]} == {ids["DBGroup"]})

    for nombre in ("Database", "IdentityDatabase"):
        comprobar(f"{nombre}: PostgreSQL privado, cifrado, respaldo y grupo esperado",
                  lambda nombre=nombre: base_correcta(nombre))
    ec2 = sesion.client("ec2")
    comprobar("Ingreso al grupo de RDS solo desde AppGroup por TCP 5432",
              lambda: ingreso_postgres(ec2.describe_security_groups(
                  GroupIds=[ids["DBGroup"]])["SecurityGroups"][0]["IpPermissions"], ids["AppGroup"]))

    gateway = sesion.client("apigatewayv2")

    def ruta_protegida():
        rutas = listar(gateway.get_routes, "Items", ApiId=ids["Http"])
        autorizador = gateway.get_authorizer(ApiId=ids["Http"], AuthorizerId=ids["Authorizer"])
        integracion = gateway.get_integration(ApiId=ids["Http"], IntegrationId=ids["ApiIntegration"])
        funcion = lambdas.get_function_configuration(FunctionName=ids["Api"])["FunctionArn"]
        destino = integracion.get("IntegrationUri", "")
        jwt = autorizador.get("JwtConfiguration", {})
        issuer = f"https://cognito-idp.{REGION}.amazonaws.com/{ids['Users']}"
        api = [r for r in rutas if r["RouteKey"] == "POST /api/{accion}"]
        return (len(api) == 1 and api[0].get("AuthorizationType") == "JWT"
                and api[0].get("AuthorizerId") == ids["Authorizer"]
                and api[0].get("Target") == "integrations/" + ids["ApiIntegration"]
                and integracion.get("IntegrationType") == "AWS_PROXY"
                and (destino == funcion or destino.endswith("/functions/" + funcion + "/invocations"))
                and set(api[0].get("AuthorizationScopes", [])) == {"openid"}
                and autorizador["AuthorizerType"] == "JWT" and jwt.get("Issuer") == issuer
                and set(jwt.get("Audience", [])) == {ids["Client"]})

    lambdas = sesion.client("lambda")
    comprobar("Ruta de operaciones: Lambda Api con JWT, emisor, cliente y scope", ruta_protegida)
    comprobar("Tres roles de ejecución Lambda distintos",
              lambda: len({lambdas.get_function_configuration(FunctionName=ids[n])["Role"]
                           for n in ("Web", "Api", "Admin")}) == 3)
    comprobar("Admin sin Function URL",
              lambda: not listar(lambdas.list_function_url_configs, "FunctionUrlConfigs",
                                 marcador="Marker", siguiente="NextMarker", FunctionName=ids["Admin"]))

    def admin_privada():
        arn = lambdas.get_function_configuration(FunctionName=ids["Admin"])["FunctionArn"]
        integraciones = listar(gateway.get_integrations, "Items", ApiId=ids["Http"])
        return all(arn not in i.get("IntegrationUri", "") for i in integraciones)

    comprobar("API HTTP de la pila sin integración a Admin", admin_privada)
    dynamo = sesion.client("dynamodb")
    comprobar("Audit con recuperación a un momento dado (PITR)",
              lambda: dynamo.describe_continuous_backups(TableName=ids["Audit"])
              ["ContinuousBackupsDescription"]["PointInTimeRecoveryDescription"]
              ["PointInTimeRecoveryStatus"] == "ENABLED")
    print("REVISIÓN MANUAL | Permisos efectivos IAM, recursos fuera de la pila, "
          "otras API e invocaciones directas de Lambda.")
    return 2 if pendientes else int(bool(diferencias))


if __name__ == "__main__":
    sys.exit(main())
