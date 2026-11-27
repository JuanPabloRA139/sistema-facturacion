"""Alta explícita de cuentas de clase. Las cuentas existentes se conservan."""
import json
import secrets

import boto3


PILA = "facturacion-servicios-lab"
ROLES = {
    "admin-demo": "administrador",
    "operador-demo": "operador",
    "auditor-demo": "auditor",
    "operador-dos": "operador",
}


def alta(cognito, secretos, funciones, pool, funcion_admin, usuario, rol):
    try:
        cognito.admin_get_user(UserPoolId=pool, Username=usuario)
    except cognito.exceptions.UserNotFoundException:
        pass
    else:
        print(f"{usuario}: cuenta existente; revisar manualmente si hubo un alta interrumpida.")
        return

    nombre = f"{PILA}/alta/{pool}/{usuario}"
    clave = secrets.token_urlsafe(32) + "aB7!"
    # La reserva por nombre impide que dos ejecuciones creen credenciales distintas.
    try:
        secretos.create_secret(
            Name=nombre,
            SecretString=json.dumps({"usuario": usuario, "temporal": clave}),
            Tags=[{"Key": "Proyecto", "Value": "FacturacionServicios"}],
        )
    except secretos.exceptions.ResourceExistsException as exc:
        raise RuntimeError(
            f"Alta pendiente o cuenta retirada: revisar {nombre} antes de continuar."
        ) from exc

    respuesta = cognito.admin_create_user(
        UserPoolId=pool, Username=usuario, TemporaryPassword=clave, MessageAction="SUPPRESS"
    )
    identificador = next(a["Value"] for a in respuesta["User"]["Attributes"] if a["Name"] == "sub")
    solicitud = {"accion": "autorizar", "sub": identificador, "rol": rol}
    resultado = funciones.invoke(FunctionName=funcion_admin, Payload=json.dumps(solicitud).encode())
    if resultado.get("FunctionError") or json.load(resultado["Payload"]).get("autorizado") is not True:
        raise RuntimeError(f"Revisar la asignación de rol de {usuario} en el directorio.")
    print(f"{usuario}: creado. Clave de primer acceso en {nombre}.")


def main():
    stack = boto3.client("cloudformation").describe_stacks(StackName=PILA)["Stacks"][0]
    salidas = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    cognito = boto3.client("cognito-idp")
    secretos = boto3.client("secretsmanager")
    funciones = boto3.client("lambda")
    for usuario, rol in ROLES.items():
        alta(cognito, secretos, funciones, salidas["UserPool"], salidas["AdminFunction"], usuario, rol)


if __name__ == "__main__":
    main()
