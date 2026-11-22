# Auditoría del sistema de facturación

**21 de noviembre de 2026 · Proyecto facturacion-local**

Se revisaron el panel, el acceso local y de Cognito, los controladores HTTP y Lambda, los casos de uso, las consultas de SQLite y PostgreSQL, los procedimientos almacenados y la plantilla de infraestructura. Se ejecutaron **28 pruebas automatizadas**, 15 en Python y 13 en JavaScript. La integración local usó el controlador HTTP y bases SQLite temporales. Los resultados corresponden al código de esta carpeta.

## Hallazgos y correcciones

| Superficie | Control revisado o cambio aplicado | Evidencia |
| --- | --- | --- |
| Inicio de sesión | El formulario captura una sola solicitud mientras se procesa. El servidor local sincroniza el contador de fallos y la tabla de sesiones. La operación de red ocurre fuera del candado. | Dos envíos del formulario produjeron una petición. Al fallar la carga del panel tras el acceso, se recuperó la sesión sin reenviar la clave. De 12 intentos inválidos concurrentes en la prueba local, 10 recibieron HTTP 401 y 2 recibieron 429. |
| Emisión y reintento | Se confirma el cliente y el total. La solicitud conserva su misma clave si se pierde la respuesta. Se guardan en la pestaña la referencia y los identificadores e importes indispensables para recuperar la emisión. El servidor verifica cliente, permisos, cantidades, precios y tasas. | Dos emisiones simultáneas con la misma clave devolvieron un folio. Reutilizarla con conceptos distintos produjo un rechazo. Una diferencia de un centavo respecto al total confirmado revirtió la operación y dejó vacío el historial de prueba. |
| Pagos y movimientos importantes | El panel confirma folio, referencia e importe del pago. También confirma la cancelación, el cambio de tarifa, el cierre, la asignación de características y el descarte del borrador. El mensaje de guardado se mantiene si falla la actualización posterior del listado. | Dos pagos simultáneos de $50.00 sobre una factura de $117.60 con la misma referencia dejaron $67.60 de saldo. Se detectó un duplicado. Otra cantidad con esa referencia fue rechazada. |
| Inyección SQL | Las consultas y las llamadas a procedimientos que reciben datos del panel vinculan sus valores mediante parámetros. El servidor toma la identidad de la sesión. El aprovisionamiento administrativo usa nombres de rol fijos y literales de contraseña escapados por PostgreSQL. | Revisión de los adaptadores y procedimientos. Se guardó y recuperó literalmente el nombre ficticio `O'Connor & Hijos <Norte>`. La configuración fija `pg8000==1.31.5`, versión corregida para CVE-2025-61385. |
| XSS | El panel construye etiquetas, opciones, tablas, comprobantes y confirmaciones mediante el DOM. Los textos de usuarios se asignan como texto. La política de contenido restringe scripts al propio origen. | La prueba de regresión revisa ambas plantillas y los archivos JavaScript en busca de salidas HTML ejecutables conocidas, manejadores HTML en línea, identificadores duplicados y referencias faltantes. |
| Validación de entrada | El servidor limita el JSON a 32 KiB y exige tipos y campos permitidos por operación. Rechaza claves repetidas, decimales JSON, controles de texto, periodos abiertos, cantidades superiores a 999, más de 30 conceptos y selecciones por lote repetidas. Los importes de la API se expresan en centavos. | Pruebas de RFC y fechas, tipos numéricos, campos desconocidos, caracteres de control, estructura JSON, tamaño, codificación y tipo de contenido. |
| Autorización | Operador, auditor y administrador tienen permisos diferenciados en el servidor. En AWS se contrasta el rol del directorio privado con el de facturación. La plantilla exige un JWT para la ruta de operaciones. | Se verificaron los roles denegados para todos los casos de uso, el rechazo de acceso a un folio ajeno y la denegación de emisión al auditor. |
| Sesiones y navegador | El servidor local comprueba origen y host, usa una cookie HttpOnly y SameSite=Strict y caduca las sesiones. Cognito usa PKCE y estado con vencimiento de 10 minutos. El token de acceso vive en memoria. Al restaurar una página desde el historial se revalida la sesión. | Pruebas locales de origen, host, cookie y caducidad. Revisión de la devolución OAuth. Se comprobaron las cabeceras de la página Lambda y su lista de archivos públicos. |

## Alcance pendiente y riesgos operativos

- **AWS Academy.** La pila `facturacion-servicios-lab` terminó en `UPDATE_COMPLETE`. Se verificó el SHA-256 de las tres funciones Lambda contra el paquete publicado. La web entregó el JavaScript y el CSS esperados, con normalización de saltos de línea. La API devolvió HTTP 401 sin sesión. El operador autenticado mediante Cognito y PKCE recibió HTTP 200 en el inicio y en la consulta de un comprobante existente, HTTP 400 al enviar un campo desconocido y HTTP 403 al consultar la auditoría. La sesión leyó 100 servicios y dos facturas. La prueba en AWS de esta versión fue de lectura y borrador. Los reintentos de escritura se comprobaron con bases temporales.
- **Interfaz.** Se abrió el panel publicado con el perfil Operador en el navegador. El borrador mostró $105.00 de subtotal, $16.80 de IVA, $4.20 de retención y $117.60 de total. La confirmación presentó el cliente y el total. Se eligió «Volver» y después se cerró la sesión. La página de escritorio se comprobó a 1440 × 900 y en la vista móvil el ancho del contenido coincidió con el área disponible.
- **Privilegios.** Las funciones Lambda usan el rol compartido de AWS Academy. Una instalación con datos reales requiere roles separados para la web, la API y el aprovisionamiento, con acceso individual a secretos y recursos. La plantilla de Cognito permite únicamente altas administrativas y no exige MFA. El perfil visible del panel muestra el rol. Las cuentas existentes de Cognito conservan sus nombres de acceso.
- **Respaldo y datos.** La plantilla configura RDS privado con cifrado y un día de retención de copias. La recuperación de un respaldo no se ensayó. SQLite guarda los datos locales en un archivo que también queda sujeto a los permisos y a la sincronización de la carpeta de Windows.
- **Dependencias.** Se inventariaron las cinco distribuciones Python incluidas en el ZIP de Lambda. PyPI devolvió cero avisos vigentes para `asn1crypto 1.5.1`, `pg8000 1.31.5`, `python-dateutil 2.9.0.post0`, `scramp 1.4.18` y `six 1.17.0` el día de la verificación. El resultado cubre esas versiones empaquetadas. El runtime administrado de Lambda y los componentes del sistema operativo quedan fuera de ese inventario.
- **Operaciones distintas.** La clave de emisión evita repetir una misma solicitud. Dos borradores creados y confirmados de forma independiente representan dos facturas válidas. Para los pagos la identificación del reintento depende de conservar la misma referencia dentro de la factura.

## Cierre del laboratorio

AWS Academy confirmó el estado Terminated y un contador de 00:00. RDS aceptó el apagado de las dos instancias. La última lectura autorizada mostró la base de facturación detenida y la de identidades en proceso de apagado. Al cerrar la sesión, AWS revocó el permiso de consulta.

## Repetir las pruebas

Desde la carpeta `facturacion`, con Python y Node.js disponibles:

```text
python -B -m unittest discover -s tests -v
node --test tests/panel.test.cjs tests/rfc.test.cjs
```

La prueba de navegador usa datos ficticios y una API en memoria. Se ejecuta con `node tests/probar-panel.cjs "ruta-al-ejecutable-de-Chrome-o-Edge"`.

## Referencias

- [OWASP · Prevención de inyección SQL](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [OWASP · Prevención de XSS](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [GitHub Advisory Database · CVE-2025-61385](https://github.com/advisories/GHSA-wq2g-r956-j8cc)

