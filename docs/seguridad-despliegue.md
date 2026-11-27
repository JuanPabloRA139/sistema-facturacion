# Operación de seguridad en AWS

## Roles de ejecución

La pila acepta WebRoleName, ApiRoleName y AdminRoleName. Por compatibilidad con Learner Lab, cada parámetro usa LabRole de forma predeterminada. Los permisos efectivos dependen de las políticas IAM reales. Para aislar privilegios, el responsable de IAM debe preparar tres roles que confíen exclusivamente en Lambda y permitan lo siguiente.

| Función | Acceso requerido |
|---|---|
| Web | Escritura en su propio grupo de logs. |
| Api | Logs propios, permisos de Lambda para su red VPC, GetSecretValue de AppSecret e IdentityAppSecret, PutItem en Audit y Query en el índice historial. |
| Admin | Logs propios, acceso VPC y GetSecretValue de los cuatro secretos técnicos de las dos RDS. |

Configura los nombres de los roles existentes, sin ruta, en WEB_ROLE_NAME, API_ROLE_NAME y ADMIN_ROLE_NAME al ejecutar infra/desplegar.sh. En una actualización, las variables omitidas conservan los valores de la pila. Verifica las políticas adjuntas, las políticas en línea y los permisos sobre los recursos. El rol del operador de despliegue necesita PassRole únicamente sobre los roles aprobados. Si la academia impone LabRole, documenta que las tres funciones continúan compartiendo permisos.

## Alta de las cuentas de presentación

El despliegue normal configura la infraestructura. Para solicitar también el alta inicial de cuentas ficticias, ejecuta CREAR_CUENTAS_DEMO=1 bash infra/desplegar.sh. También puedes ejecutar AWS_DEFAULT_REGION=us-east-1 python3 infra/usuarios_demo.py sobre una pila ya inicializada. El script omite las cuentas existentes y registra las nuevas con contraseña temporal. Cognito solicita cambiarla en el primer acceso. Cada contraseña inicial está en facturacion-servicios-lab/alta/<pool>/<usuario>. El responsable de IAM debe limitar GetSecretValue al personal que autoriza o entrega esa cuenta.

En una actualización desde la versión anterior, el secreto accesos-demo puede contener contraseñas todavía válidas. Restringe sus lectores, cambia las contraseñas antiguas en una ventana coordinada y verifica que el personal pueda acceder con los nuevos datos antes de retirar el secreto antiguo. La aplicación nunca entrega estos secretos al navegador.

## Recuperar un alta interrumpida

Si se creó el secreto individual pero Cognito aún carece de la cuenta, el operador comprueba su origen y si hubo una retirada intencional. Puede completar el alta inicial con la contraseña temporal reservada mediante los controles administrativos de Cognito. Si Cognito ya contiene la cuenta, confirma en el grupo de la pila su sub, su estado, el rol aprobado y los registros de identidades y facturación. Si los roles ya coinciden con lo aprobado, el alta terminó. Si falta una asignación, una persona autorizada puede invocar la Lambda privada Admin con la acción autorizar, ese sub y el rol verificado. Si alguien cambió el rol con posterioridad, prevalece la decisión aprobada más reciente. Una contraseña temporal vencida se recupera mediante el flujo administrativo de Cognito. Los datos de acceso se entregan individualmente.
