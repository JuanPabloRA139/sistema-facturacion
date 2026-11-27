# Entrega AWS · Sistema de Facturación y Servicios
Las observaciones de este documento corresponden a los despliegues anteriores al endurecimiento de seguridad. Para comprobar el estado de la pila actual, consulta [operación en AWS](conexion-aws.md).

## Aplicación desplegada
- Región us-east-1. Pila facturacion-servicios-lab. Última actualización comprobada en estado UPDATE_COMPLETE.
- URL pública del panel: consultar la salida de API Gateway en la pila del laboratorio
- Instancia PostgreSQL del proyecto: base de facturación. Cifrada, privada, Single-AZ, db.t4g.micro y 20 GB.
- La inicialización devolvió 100 servicios, 50 características y 10 procedimientos instalados. DynamoDB informó ACTIVE, PAY_PER_REQUEST e índice historial ACTIVE.
- Cognito autenticó un administrador, dos operadores y un auditor. Las claves se administran en Secrets Manager. Cada usuario recibe solo su clave por un canal privado.
- Al final del despliegue se solicitó detener RDS. Para usar las operaciones de datos hay que iniciarla y esperar a que figure Disponible.
## Alcance comprobado
El panel respondió públicamente, el esquema se aplicó y las cuatro identidades se asociaron a sus roles. La demo local ya emitió una factura y aplicó un pago parcial. La verificación funcional posterior está documentada al final de este archivo. Los archivos SQL 05 y 07 son de pruebas y no se ejecutaron en AWS.
## Actualización para dos instancias
Las verificaciones anteriores corresponden al despliegue inicial con una instancia. La revisión del profesor exige dos instancias físicas y RFC con formato correcto. El paquete actualizado amplía la misma pila con IdentityDatabase privada y cifrada y un usuario de lectura independiente. La inicialización migra los roles existentes una sola vez. Ejecutar infra/desplegar.sh actualiza la pila y prepara ambas bases. El script deja ambas disponibles para la demostración. Al acabar, detener ambas en RDS.
El 21 de noviembre se comprobaron las dos instancias privadas disponibles, el acceso de los cuatro usuarios y los diez procedimientos mediante la API desplegada. El panel mostró el comprobante del folio 1 con $67.60 de saldo. Véase [la verificación con evidencias](evidencias/verificacion-aws.md). GitHub requiere las contribuciones de los cuatro integrantes.
