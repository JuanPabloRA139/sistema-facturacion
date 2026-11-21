# Sistema de facturación y servicios · versión local integrada
## Arrancar en Windows
1. Descomprime todo el ZIP en una carpeta con permiso de escritura. Ejecuta INICIAR.cmd.
2. Se abre el panel en tu navegador. La ventana de inicio muestra una clave temporal para cada usuario. Entra como operador para la primera factura o como admin para todas las operaciones.
3. Conserva esa ventana abierta mientras trabajas. Ctrl+C detiene el servidor. Al volver a abrirlo cambian las claves y el puerto, y las facturas siguen en datos-locales/facturacion.sqlite.
El lanzador usa Python 3.10 o posterior. En esta PC también detecta el Python incluido en Blender. Arranque manual desde la raíz: python -B servidor.py --abrir. Todo el flujo funciona sin servicios externos. Usa datos ficticios.
## Primera prueba de cinco minutos
- Entra como operador, elige Cliente de muestra y añade una unidad del primer servicio. En un catálogo recién creado su precio es $105.00. Pulsa Emitir factura. Debe mostrar subtotal $105.00, IVA de ejemplo $16.80, retención de ejemplo $4.20 y total $117.60.
- Anota el folio. En Facturas y pagos registra $50.00 con referencia DEMO-1. Debes ver saldo $67.60. Repetir la misma referencia e importe conserva el saldo.
- Sal y entra como operador2. La factura anterior queda fuera de su lista. Como auditor puedes consultar y como admin puedes cambiar una tarifa, asignar características o cancelar una factura sin pagos.
- Para probar descuentos agrega diez unidades de un servicio. El servidor descuenta 5 % antes de calcular los impuestos. Los importes viajan como enteros en centavos. Los impuestos y reglas son ficticios.
- En Reportes consulta saldos y auditoría. Para el cierre usa un día o mes ya terminado. Un periodo de prueba sin movimientos produce cero. El cierre lee emisiones y reversiones según su fecha y guarda el resultado.
## Dónde estudiar
| Archivo | Qué ocurre |
|---|---|
| frontend/panel.html y panel.js | Capturan la operación y presentan la respuesta del servidor. El HTML aislado index.html es el prototipo anterior de RFC. |
| servidor.py | Sirve el panel en loopback, comprueba sesión y origen, inicia transacciones y traduce errores a HTTP. |
| backend/servicios.py y rfc.py | Validan permisos, entradas y RFC en modo local y AWS. |
| backend/local.py y rds.py | Adaptan las mismas operaciones a SQLite y PostgreSQL, respectivamente. |
| database/local.sql | Esquema relacional SQLite utilizado al iniciar, con claves, índices y restricciones. |
| tests/test_local.py | Recorre las rutas del servidor con una base temporal y solicitudes simultáneas. |
| docs/estudio | Guías individuales del plan del curso. Las referencias a JWT, RDS y DynamoDB describen la etapa AWS. |
## Pruebas
Desde la raíz ejecuta **python -B -m unittest discover -s tests -v** y **node --test tests/rfc.test.cjs**. Por defecto la prueba del servidor usa mensajes HTTP en memoria y una base SQLite real. En una terminal que permita conexiones locales establece PRUEBA_CON_RED=1 para ejecutar el mismo recorrido por TCP.
## Alcance de esta versión
Servidor de desarrollo para una sola PC, datos ficticios y sesiones temporales de una hora. El almacenamiento local depende del acceso a la carpeta por parte del usuario de Windows. Usa clientes de prueba y mantén datos-locales fuera de cualquier entrega. La validación del RFC revisa estructura y fecha. El comprobante se muestra en JSON con importes en centavos.
## Versión AWS
La carpeta infra incluye la plantilla de CloudFormation, el despliegue para CloudShell y el alta de usuarios de demostración. La API conecta los diez procedimientos de PostgreSQL, Cognito y la auditoría en DynamoDB. Consulta [el manual de AWS](docs/conexion-aws.md), [los diagramas](docs/arquitectura.md) y [OpenAPI](docs/openapi.json). Las guías individuales están en docs/estudio. Esta versión define dos instancias PostgreSQL. RDS de identidades es la autoridad de roles y RDS de facturación procesa las operaciones. La API HTTP llama a backend/servicios.py, que delega las consultas a backend/rds.py. El modo local de práctica usa SQLite.