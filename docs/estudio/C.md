# Dahi · Frontend

[Mi contribución y criterio de aceptación](reparto.md)

## Segmentos que debes ubicar
frontend/panel.html, panel.js, rfc.js y acceso-aws.js.

En el panel publicado, panel.js recoge el formulario, valida el RFC con formatoRfcValido y envía la solicitud a la API. La respuesta se presenta con textContent. El borrador de emisión permite revisar cliente y total antes de confirmar.
## Tres preguntas para practicar
1. **¿Qué comprueba la expresión y qué comprueba la fecha?** La expresión revisa letras, fecha de seis dígitos y sufijo. Se reconstruye la fecha y se comparan mes y día para detectar fechas imposibles.
2. **¿Una respuesta positiva prueba que existe en el SAT?** Solo acredita la forma preliminar. La inscripción requiere consulta oficial y el estado del sistema debe distinguirla.
3. **¿Dónde se determina el importe definitivo?** La interfaz presenta datos. El servidor recupera precios y aplica reglas vigentes en PostgreSQL.
## Ejercicio sin apuntes
Ejecutar las pruebas y mostrar el formulario con un caso aceptado y uno con fecha imposible. Abre tu PR, señala la función real y explica su entrada, salida, llamada siguiente y un error. Pide a otro integrante que cambie el ejemplo. Intercambien guías y repitan toda respuesta incompleta antes del lunes y de la final.
