# Juan Pablo · Backend y API

[Mi contribución y criterio de aceptación](reparto.md)

## Segmentos que debes ubicar
backend/api_aws.py, backend/servicios.py, backend/identidades.py, backend/rds.py, backend/rfc.py y docs/openapi.json.

API Gateway entrega identidad validada; Python valida el cuerpo, consulta rol y ámbito, pasa parámetros al SQL y traduce el resultado a HTTP.
## Tres preguntas para practicar
1. **¿Puede un operador elegir otra factura en la URL?** Puede enviar un identificador distinto. La consulta debe restringirse por el ámbito autorizado del usuario.
2. **¿Cómo llega un nombre con apóstrofo a SQL?** El controlador pasa el valor como parámetro separado de la instrucción SQL.
3. **¿Por qué repetir la validación de RFC en el servidor?** Un cliente puede saltarse el formulario y enviar una petición directa. El servidor aplica las reglas antes de guardar.
## Ejercicio sin apuntes
Seguir una solicitud desde el contrato OpenAPI hasta el procedimiento y mostrar una denegación. Abre tu PR, señala la función real y explica su entrada, salida, llamada siguiente y un error. Pide a otro integrante que cambie el ejemplo. Intercambien guías y repitan toda respuesta incompleta antes del lunes y de la final.
