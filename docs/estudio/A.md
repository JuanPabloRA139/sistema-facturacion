# Mauricio · Base de datos

[Mi contribución y criterio de aceptación](reparto.md)

## Segmentos que debes ubicar
database/03_facturacion.sql, 04_procedimientos.sql, 06_operaciones.sql y 08_auditoria.sql.

Python entrega cliente, conceptos y clave de operación. PostgreSQL bloquea la serie, valida y escribe encabezado, detalle y folio en una transacción. Devuelve identificador y totales.
## Tres preguntas para practicar
1. **¿Qué impide duplicar un folio?** Bloqueo de la serie en la transacción más restricción única. La clave de operación permite reconocer un reintento.
2. **¿Por qué guardar el precio en el detalle?** La tarifa cambia con el tiempo. La línea conserva el precio e impuestos vigentes al emitir.
3. **¿Quién inicia el cálculo y cómo compruebas el resultado?** La ruta de emisión llama al procedimiento parametrizado. Comparo subtotal, descuentos, retenciones y total contra un caso manual.
## Ejercicio sin apuntes
Mostrar una emisión con dos conceptos y el resultado de repetirla. Abre tu PR, señala la función real y explica su entrada, salida, llamada siguiente y un error. Pide a otro integrante que cambie el ejemplo. Intercambien guías y repitan toda respuesta incompleta antes del lunes y de la final.
