# Verificación funcional en AWS Academy

Fecha de ejecución: 21 de noviembre de 2026, 06:25 UTC (00:25 en Ciudad de México). Pila `facturacion-servicios-lab`, región `us-east-1`. Las dos instancias PostgreSQL estaban disponibles y eran privadas. Las llamadas utilizaron la API HTTPS publicada y sesiones reales de Cognito con las cuatro cuentas de demostración. Importes en MXN.

| Procedimiento | Operación y resultado observado |
| --- | --- |
| emitir_factura | Cliente ficticio 1. Una unidad del servicio de prueba 1 generó el folio 1. Repetir la misma solicitud devolvió el mismo folio. |
| aplicar_descuento | Una unidad tuvo descuento cero. Diez unidades en el folio 2 sumaron $1,050.00 y recibieron $52.50 de descuento. |
| calcular_importes | En el folio 1 el subtotal fue $105.00, el IVA $16.80, la retención $4.20 y el total $117.60. En el folio 2, tras el descuento, el IVA fue $159.60, la retención $39.90 y el total $1,117.20. |
| registrar_pago | Un pago de $50.00 en el folio 1 dejó $67.60 pendientes. Repetir la referencia mantuvo el saldo y la API indicó que el pago estaba duplicado. |
| generar_comprobante | El auditor pudo leer el folio 1. En el navegador, el operador abrió el mismo comprobante y vio $117.60 de total, $50.00 pagados y $67.60 de saldo. |
| antiguedad_saldos | El reporte del auditor incluyó el folio 1 con saldo de $67.60 y cero días vencidos. |
| cancelar_factura | El administrador canceló el folio 2, que estaba sin pagos. Repetir la cancelación mantuvo el saldo en cero. Intentar cancelar el folio 1 con pago parcial devolvió HTTP 409. |
| cerrar_periodo | El administrador cerró el 15 de enero de 2000 y el mes de enero de 2000. Ambos periodos de prueba dieron neto cero, también al repetirlos. |
| asignar_caracteristicas | El administrador envió un lote de dos servicios por dos características. La API aceptó cuatro asignaciones en cada intento. Este resultado mide la respuesta de la API. La verificación no incluyó un conteo directo de filas en PostgreSQL. |
| cambiar_tarifa | El servicio pasó de $105.00 a $105.01 y se restauró a $105.00. Se consultó el catálogo tras ambos cambios. El comprobante anterior conservó su precio de $105.00 y su total de $117.60. |

## Acceso y auditoría

- Cognito autenticó dos operadores, un auditor y un administrador. La API devolvió HTTP 401 sin sesión.
- El segundo operador recibió un listado sin el folio 1 y obtuvo HTTP 404 al solicitar ese comprobante. El auditor recibió HTTP 403 al intentar registrar un pago. Un RFC con fecha inválida fue rechazado con HTTP 400.
- La consulta de auditoría del sistema, respaldada por DynamoDB, devolvió una emisión y un pago para el folio 1, y una emisión y una cancelación para el folio 2. También mostró los eventos de tarifa del servicio.

## Evidencia

El equipo conserva las capturas de la verificación y del comprobante del folio 1 en la carpeta local de evidencias.

La ejecución dejó el cliente y los folios ficticios disponibles para la demostración, junto con su historial, los cierres de prueba y las asociaciones del lote. El recorrido cubrió los diez procedimientos a través de la API. En la interfaz se revisaron el historial y el comprobante.
