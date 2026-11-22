# Sistema de facturación y servicios

## Iniciar el sistema

Descarga o clona el proyecto. En Windows, ejecuta `INICIAR.cmd`. También puedes iniciar el panel con `python -B servidor.py --abrir` desde la carpeta del proyecto con Python 3.10 o posterior. La ventana de inicio muestra las claves temporales. Los datos de práctica se guardan en SQLite, en `datos-locales/`.

## Emitir la primera factura

1. Entra como operador y selecciona el cliente de muestra.
2. Agrega una unidad del primer servicio. En una base nueva, el subtotal es $105.00 y el total es $117.60.
3. Confirma la factura y abre su folio. Registra un pago de $50.00 con la referencia `PAGO-01`. El saldo debe quedar en $67.60. Si repites el pago con la misma referencia e importe, el saldo se conserva.

Las tarifas y los datos son ficticios. La validación del RFC comprueba su formato y fecha.

## Reparto del equipo

| Integrante | Responsabilidad | Qué puede mostrar |
|---|---|---|
| Dahi | Interfaz del operador | Preparar el borrador, revisar los conceptos y volver desde la confirmación. |
| Juan Pablo | Backend | Seguir el alta de un cliente y comprobar qué pasa si cambia el total al emitir. |
| Mauricio | Base de datos | Seguir un folio y verificar que cancelar la misma factura dos veces produce una sola reversión. |
| Martín | Pruebas y despliegue | Reproducir el recorrido de una factura y medir la consulta de un comprobante. |

Cada integrante parte de `main`, registra su cambio con su cuenta y abre una solicitud de revisión con la prueba que realizó.

## Pruebas

Desde la carpeta del proyecto:

```console
python -B -m unittest discover -s tests -v
node --test tests/panel.test.cjs tests/rfc.test.cjs
```

Los archivos de `database/` incluyen el esquema local y los procedimientos de PostgreSQL. En Windows puedes ejecutar sus pruebas con `PROBAR-FACTURACION.cmd`.
