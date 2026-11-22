# Reparto del sistema de facturación

Los cuatro trabajan sobre la misma aplicación. Cada persona tiene un área principal, una mejora acotada que puede desarrollar y probar, y una pregunta que debe poder contestar siguiendo el código. Los títulos de commit son propuestas para el trabajo que haga cada integrante.

| Integrante | Área y archivos de referencia | Rama propuesta | Revisa su PR |
|---|---|---|---|
| Dahi | Pantallas y experiencia del operador. `frontend/panel.html`, `panel.css`, `panel.js` y `rfc.js` | `feat/frontend-dahi` | Juan Pablo |
| Juan Pablo | Backend y contrato HTTP. `backend/api_aws.py`, `entrada.py`, `servicios.py`, `rds.py` y `docs/openapi.json` | `feat/backend-juanpablo` | Mauricio |
| Mauricio | Esquema, integridad, importes y pruebas funcionales de facturación (`tests/test_local.py`). `database/03_facturacion.sql`, `04_procedimientos.sql`, `06_operaciones.sql` y sus pruebas SQL | `feat/datos-mauricio` | Martín |
| Martín | Despliegue, disponibilidad de los servicios y medición de latencia. `infra/cloudformation.json`, `infra/desplegar.sh` y las evidencias | `test/integracion-martin` | Dahi |

## Dahi · Qué ve el operador si falta el cliente

**Contribución propuesta.** Cuando ya hay conceptos en el borrador pero falta seleccionar un cliente, mostrar junto a «Emitir factura» qué falta. Al elegir el cliente, retirar la indicación y permitir la confirmación. El botón ya comprueba estos requisitos. El cambio consiste en hacer visible la causa y mantener el mensaje accesible por teclado.

**Evidencia para su PR.** Probar el mismo borrador antes y después de seleccionar el cliente. Elegir «Volver» en la confirmación y comprobar que conserva el concepto. Incluir una prueba del comportamiento o las capturas de ambos estados. Posible commit: `Explica por qué el borrador aún no se puede emitir`.

**Para estudiar.** Seguir el clic desde el botón hasta `actualizarResumen` y el diálogo de confirmación. ¿Qué ve la persona antes de enviar la factura y qué sucede si se arrepiente? [Guía de Dahi](C.md)

## Juan Pablo · Backend y contrato de la API

**Contribución propuesta.** Documentar en OpenAPI la emisión tal como la acepta el backend. Incluir la clave de reintento, los conceptos, el total esperado opcional en centavos y la respuesta de conflicto cuando el importe cambió. Añadir una prueba que detecte si el contrato deja de describir ese comportamiento.

**Evidencia para su PR.** Mostrar dos solicitudes de ejemplo con la misma estructura. Una coincide con el importe calculado. La otra difiere en un centavo y produce un conflicto en la API de AWS. Usar pruebas locales con dependencias simuladas para revisar la respuesta. Posible commit: `Documenta y prueba el contrato de emisión con total esperado`.

**Para estudiar.** Seguir `api_aws.handler` → `servicios.emitir` → `repo.emitir`. ¿Quién determina el precio y en qué punto se impide confirmar la transacción si cambió el total? [Guía de Juan Pablo](B.md)

## Mauricio · Integridad de datos y pruebas de facturación

**Contribución propuesta.** Reforzar la prueba SQL de cancelación repetida en `database/07_prueba_operaciones.sql`. El caso existente comprueba que hay una reversión con el importe esperado. Ampliarlo para comprobar cuántas reversiones existen para el folio, la suma de sus importes y el estado final de la factura.

**Evidencia para su PR.** En la base temporal, cancelar dos veces el mismo folio. Demostrar una sola reversión, la suma igual al negativo del total original y el estado «cancelada». Explicar qué aportan la clave de la tabla y el bloqueo del procedimiento. Posible commit: `Comprueba cantidad y saldo de reversiones al repetir una cancelación`.

**Responsabilidad de integración.** Mauricio prepara el caso de prueba y lo presenta. Con datos ficticios, emite una factura, registra un pago parcial y repite el pago con la misma referencia e importe. Guarda el folio y el saldo después de cada intento. El saldo debe bajar una sola vez. Después intenta consultar el folio con un segundo operador y comprueba que la respuesta no contiene el comprobante. En la evidencia anota el entorno, el resultado esperado y el observado.

**Para estudiar.** Localizar `cancelar_factura`, el bloqueo de la fila y la clave primaria de `reversiones`. ¿Qué vería otro proceso si intenta cancelar el mismo folio al mismo tiempo? [Guía de Mauricio](A.md)

## Martín · Despliegue, disponibilidad y rendimiento

**Contribución propuesta.** Crear una medición reproducible de consulta de comprobantes sobre datos ficticios locales. Preparar un folio temporal, hacer un calentamiento y medir una serie acotada de lecturas, por ejemplo 20. Registrar entorno, número de respuestas correctas, errores y percentil 95 en milisegundos. Identificar si se midió el controlador en memoria o el recorrido por HTTP.

**Evidencia para su PR.** Entregar el comando, la salida y una interpretación breve del p95. Otra persona debe poder repetir el ensayo en su equipo. Para la exposición, Martín identifica la URL de la pila, comprueba que las dos instancias RDS estén disponibles y entrega la URL a Mauricio. Mauricio realiza las pruebas de facturación. Juan Pablo explica el recorrido API Gateway → Lambda → RDS. Si falla la demo, Martín revisa el estado de los servicios y la conectividad. Juan Pablo revisa la petición, los permisos del usuario y la respuesta de la API. Posible commit: `Mide la latencia de consulta de comprobantes en una base temporal`.

**Para estudiar.** ¿Qué tramo mide el ensayo local y qué componentes se añaden en AWS? ¿Cómo se verificó que ambas bases estaban disponibles antes de probar el sistema? [Guía de Martín](D.md)

## Cómo registrar los aportes

1. Juan Pablo publica la versión actual como base compartida del equipo. Antes de subirla, revisa los archivos incluidos y deja fuera las bases locales, claves y tokens.
2. Cada integrante acepta la invitación con su cuenta, parte de la misma base, abre su rama y desarrolla su mejora. Registra los commits con su propia identidad y abre su PR con el cambio, la prueba y el resultado.
3. El compañero indicado en la tabla reproduce el caso y deja su revisión. Para la entrega, guarden el enlace al PR y al commit de cada integrante.

En el ensayo, Martín muestra que el entorno está listo y pasa la URL a Mauricio. Dahi presenta el borrador y Juan Pablo explica cómo la API valida la solicitud. Mauricio demuestra la emisión, el pago repetido y el acceso con otro operador. Mauricio explica qué restricciones protegen los datos. Martín cierra con el resultado de su medición de latencia.
