# Verificación local de facturación

Los diez casos de `tests/test_verificacion_facturacion.py` pasan por los servicios del backend y usan una base SQLite nueva en memoria para cada prueba. Se ejecutaron en la copia local del proyecto completo, que incluye las ramas de trabajo en su versión base. Para reproducirlos se requieren el backend y el esquema local.

| Caso comprobado | Resultado esperado y observado |
|---|---|
| Emisión de una unidad | Subtotal $105.00, IVA $16.80, retención $4.20 y saldo inicial $117.60. |
| Reintento de emisión | Un solo folio, una línea de detalle y un solo movimiento de emisión. |
| Cambio posterior de tarifa | La factura original conserva $117.60 y una emisión nueva suma $224.00. |
| Pago parcial | Un pago de $50.00 deja $67.60 tanto en el comprobante como en cartera. |
| Repetición del pago | Una fila de pago y un evento de pago. El saldo sigue en $67.60. |
| Misma referencia con otro importe | El servicio rechaza el intento y conserva el importe original. |
| Liquidación del último centavo | Saldo cero, estado pagada y folio fuera del reporte de pendientes. |
| Segundo operador | Su listado excluye el folio y el servicio rechaza leerlo o cobrarlo. |
| Auditor | Lee el saldo de $67.60. El intento de cobro se rechaza. |
| Cancelación repetida sin pagos | Una emisión y una sola reversión por el mismo importe. |

Desde la raíz del proyecto integrado:

```console
python -B -m unittest discover -s tests -p test_verificacion_facturacion.py -v
```

Resultado de esta ejecución local: diez casos aprobados. La suite local completa registró 27 pruebas Python y 13 de Node aprobadas. La demostración por navegador y el despliegue en AWS se verifican por separado.
