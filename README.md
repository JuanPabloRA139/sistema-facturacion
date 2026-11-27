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

Los archivos de `database/` incluyen el esquema local y los procedimientos de PostgreSQL. En Windows, `PROBAR-FACTURACION.cmd` prepara PostgreSQL embebido y ejecuta el recorrido transaccional. Para comprobar también el directorio y los permisos efectivos, ejecuta en PowerShell desde la raíz del proyecto:

```powershell
$motor = Join-Path $env:LOCALAPPDATA 'FacturacionServicios/pruebas-pg-0.5.10'
$node = Join-Path $motor 'node_modules/.bin/node.cmd'
& $node tests/probar-directorio.cjs $motor
& $node tests/probar-permisos.cjs $motor
& $node tests/probar-saldos.cjs $motor
```

Para ejecutar también las pruebas HTTP locales en PowerShell, usa `$env:PRUEBA_CON_RED='1'` antes de invocar unittest. El recorrido visual reproducible usa una API en memoria y acepta la ruta al ejecutable de Edge o Chrome mediante `node tests/probar-panel.cjs "RUTA_AL_NAVEGADOR"`.

## Entrega y evidencias

- [Modelo de datos, contexto C4 y arquitectura en AWS](docs/arquitectura.md)
- [Contrato de las once operaciones de la API](docs/openapi.json)
- [Despliegue y operación en AWS Academy](docs/conexion-aws.md)
- [Permisos de las funciones y credenciales de presentación](docs/seguridad-despliegue.md)
- [Evidencia funcional del 21 de noviembre en AWS](docs/evidencias/verificacion-aws.md)
- [Auditoría funcional del 27 de noviembre y cambios de esta candidata](docs/auditoria-funcional-2026-11-27.pdf)

Para comprobar la paginación desde el panel, entra en Reportes, abre la cartera de saldos y utiliza Siguiente cuando queden folios. La API documenta también el modo de consulta anterior para mantener compatibilidad con los clientes existentes. La primera ejecución local de esta candidata separa el motivo de las cancelaciones antiguas de la bitácora mostrada en el panel; al trabajar con datos que deban conservarse, respáldalos antes de actualizar.
