# Martín · Despliegue, disponibilidad y rendimiento

[Mi contribución y criterio de aceptación](reparto.md)

## Segmentos que debes ubicar
infra/cloudformation.json, infra/desplegar.sh, backend/auditoria_aws.py y docs/conexion-aws.md.

API Gateway aplica la autorización JWT. Lambda recibe la petición y accede a RDS por red privada. Un entregador publica eventos pendientes en DynamoDB.
## Tres preguntas para practicar
1. **¿Qué conecta la función a RDS?** La configuración de VPC, subredes, grupos de seguridad y endpoint permite la conexión; el usuario de BD y TLS protegen el acceso.
2. **¿Qué pasa si DynamoDB falla al cambiar una tarifa?** El cambio y su evento se guardan juntos en RDS. El entregador reintenta con la misma clave y evita duplicados.
3. **¿Cómo se demuestra que el despliegue es repetible?** Otro integrante sigue el README con credenciales temporales propias y reproduce una factura, una consulta de auditoría y un rechazo por permisos.
## Ejercicio sin apuntes
Ubica la URL de la pila y muestra el estado de ambas instancias RDS. Pasa la URL a Mauricio para que él demuestre la emisión, el pago repetido y los permisos. Presenta tu medición de latencia e indica dónde la realizaste. Abre tu PR, señala la función real y explica su entrada, salida, llamada siguiente y un error. Pide a otro integrante que cambie el ejemplo. Intercambien guías y repitan toda respuesta incompleta antes del lunes y de la final.

Identifica las salidas Database e IdentityDatabase. Explica qué ocurre si una está detenida y muestra cómo iniciar y detener ambas.
