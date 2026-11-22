# Operación del sistema en AWS Academy
## Despliegue
En CloudShell de us-east-1, descomprime el paquete del proyecto y ejecuta `bash infra/desplegar.sh`. El script empaqueta la aplicación Python y el certificado oficial de RDS, sube el ZIP a un bucket privado del laboratorio, aplica la plantilla de CloudFormation e inicializa PostgreSQL. Requiere autorización del laboratorio para los servicios descritos y LabRole preexistente. El script no ejecuta los archivos SQL de pruebas.

La pila se llama **facturacion-servicios-lab**. En CloudFormation → pilas → Salidas aparecen **Url**, **Database**, **IdentityDatabase**, **UserPool**, **AuditTable** y **AdminFunction**. El paquete de Lambda se identifica por su hash para admitir actualizaciones. Las credenciales de AWS Academy se renuevan iniciando sesión en el lab. Las cuentas de la aplicación se autentican independientemente con Cognito.

## Acceso de la clase
En Secrets Manager abre el secreto **facturacion-servicios-lab/accesos-demo** desde tu propia sesión para recuperar únicamente la clave del usuario que vas a utilizar. El panel abre la página de Cognito. Las cuentas **admin-demo**, **operador-demo**, **operador-dos** y **auditor-demo** tienen permisos asignados en PostgreSQL. Al comenzar, da de alta un cliente ficticio antes de emitir su primera factura. El primer servicio del catálogo tiene una tarifa de $105 MXN. Los importes y las tasas son de demostración académica.

## Inicio y parada
Usa las salidas Database e IdentityDatabase para identificar las dos instancias de este proyecto. Aplica los pasos siguientes a ambas. En RDS → Bases de datos → instancia → Acciones, selecciona Iniciar antes de la exposición. Espera a que figure Disponible. Al finalizar selecciona Detener temporalmente. El almacenamiento, los secretos, los respaldos aplicables y el endpoint privado pueden seguir generando cargos. RDS reinicia una instancia automáticamente tras siete días detenida.
## Estructura
El navegador obtiene HTML de una Lambda pública que sirve únicamente archivos permitidos. Cognito usa Authorization Code con PKCE. El token de acceso se mantiene en memoria hasta salir, expirar o recargar. API Gateway valida los JWT para POST /api/{accion}. El backend obtiene la identidad de la petición autorizada y consulta el directorio en IdentityDatabase y verifica la copia operativa en Database. Los secretos de base nunca pasan al navegador. PostgreSQL usa SSL con verificación del nombre y la cadena de confianza.
## Auditoría
Los disparadores registran emisión, pago, cancelación y cambio de tarifa en eventos_pendientes dentro de la transacción del negocio. Después del commit, la API intenta publicar un lote en DynamoDB mediante una clave única. Los eventos pendientes se recuperan en operaciones posteriores o al consultar auditoría. El índice historial permite lecturas recientes de hasta cien eventos. Puede haber un breve retraso de propagación.
## Entrega y cierre del laboratorio
Conserva código, diagramas y evidencias en el repositorio compartido. Antes de retirar definitivamente la pila después de la presentación, decide qué datos y respaldos necesitas conservar. La parada de RDS y la eliminación de infraestructura son acciones distintas. El bucket de paquetes y el secreto de accesos demo se administran fuera de CloudFormation y requieren revisión al retirar el proyecto.

