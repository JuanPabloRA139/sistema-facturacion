# Mauricio · Base de datos

[Mi contribución y criterio de aceptación](reparto.md)

## Segmentos que debes ubicar
database/03_facturacion.sql, 04_procedimientos.sql, 06_operaciones.sql y 08_auditoria.sql.

Python entrega cliente, conceptos y clave de operación. PostgreSQL bloquea la serie, valida y escribe encabezado, detalle y folio en una transacción. Devuelve identificador y totales.
## Tu parte de la integración
Martín te entrega la URL del panel y confirma que las dos instancias RDS están disponibles. Tú preparas los datos ficticios, realizas la prueba funcional y explicas el resultado. Muestra el folio emitido, el saldo después del primer pago y el saldo después de repetir ese pago con la misma referencia. Luego consulta el folio con otro operador y comprueba que no se expone el comprobante.

Para ensayarlo en local, ejecuta desde la raíz `python -B -m unittest discover -s tests -p test_local.py -v`. Ubica `test_recorrido` y `test_importe_confirmado_y_reintentos`. Al presentar resultados, indica si corresponden al ensayo local o a la API desplegada.

Para la demostración, emite una unidad del servicio de muestra de $105.00. El total con los impuestos de ejemplo es $117.60. Registra un pago de $50.00 y repítelo con la misma referencia. Muestra el mismo saldo de $67.60 en ambas consultas. Comprueba que el folio queda fuera del alcance del segundo operador y que el auditor puede consultar el saldo. Guarda el folio y el resultado de cada paso.

## Tres preguntas para practicar
1. **¿Qué impide duplicar un folio?** Bloqueo de la serie en la transacción más restricción única. La clave de operación permite reconocer un reintento.
2. **¿Por qué guardar el precio en el detalle?** La tarifa cambia con el tiempo. La línea conserva el precio e impuestos vigentes al emitir.
3. **¿Quién inicia el cálculo y cómo compruebas el resultado?** La ruta de emisión llama al procedimiento parametrizado. Comparo subtotal, descuentos, retenciones y total contra un caso manual.
## Ejercicio sin apuntes
Mostrar una emisión con dos conceptos y el resultado de repetirla. Abre tu PR, señala la función real y explica su entrada, salida, llamada siguiente y un error. Pide a otro integrante que cambie el ejemplo. Intercambien guías y repitan toda respuesta incompleta antes del lunes y de la final.
