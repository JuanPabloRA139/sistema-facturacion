# Plan de trabajo inicial del 19 al 26 de noviembre

Esta lista conserva los nombres de archivos y las metas previstos al iniciar el proyecto. El inventario entregable, los resultados comprobados y las diferencias con el despliegue se encuentran en la [auditoría funcional del 27 de noviembre](auditoria-funcional-2026-11-27.pdf). La especificación vigente es [OpenAPI en JSON](openapi.json).

Marcar una tarea después de integrar su pull request y adjuntar una prueba con datos ficticios. El reparto del equipo es A = Mauricio, B = Juan Pablo, C = Dahi y D = Martín. Las cuatro contribuciones propuestas y sus criterios de aceptación están en [el reparto por integrante](estudio/reparto.md).
## Preparación conjunta · 19–20
- [ ] Crear repositorio GitHub e invitar a las cuatro cuentas con permiso de escritura. Cada persona acepta desde su cuenta. Mantener privado salvo indicación docente.
- [ ] Crear issues con responsable, fecha y criterio de aceptación. Usar main para integración y una rama por tarea, por ejemplo feat/modelo, feat/api-facturas, feat/interfaz-rfc, infra/laboratorio.
- [ ] Cada integrante crea su rama desde main actualizado, desarrolla y prueba un cambio propio, hace commit con su identidad, hace push desde su cuenta y abre PR. Otra persona revisa y verifica el resultado. Conservar los enlaces a cuatro PR y commits. La plantilla inicial debe atribuirse como base compartida.
- [ ] D verifica presupuesto, permisos de Cognito, VPC, conexión a RDS y acceso privado de Lambda a DynamoDB. Resolver 1 o 2 instancias con el profesor. Registrar decisión en docs/arquitectura.md.
- [ ] A y B acuerdan argumentos, resultados y errores de cada procedimiento. B y C acuerdan rutas y campos en docs/openapi.yaml antes de conectar pantallas.
## Corte del lunes · terminar el domingo y verificar el lunes
- [ ] A crea database/schema.sql, seed.sql y procedures.sql separados. Incluir Clientes, Facturas, Detalle_Factura, Servicios, Caracteristicas_Servicio, Pagos, Impuestos_Historico y Usuarios_Roles. Añadir catálogo de características, asignaciones, series y restricciones. Registrar DER y consultas de conteo.
- [ ] A implementa folios atómicos, importes decimales, descuentos, validación de pagos y estructura de comprobante. Guardar instantáneas de precios e impuestos. Probar emitiendo dos solicitudes distintas y repitiendo una.
- [ ] B crea backend con entrada HTTP, validación, autorización por rol y ámbito y acceso SQL parametrizado. Integrar alta de cliente, catálogo, emisión, pago y comprobante. Guardar una clave de operación única para reintentos.
- [ ] B y C integran validación de RFC en servidor y validación inmediata en HTML. Probar longitudes, fecha y caracteres. Evitar que se guarde un RFC rechazado aunque se omita la interfaz. Acordar con el profesor si requiere dígito verificador, RFC genéricos o confirmación oficial; documentar esas reglas y ampliar los casos antes de declarar completo el requisito.
- [ ] Si se exige inscripción real, habilitar consulta manual en portal SAT y registro restringido de resultado, fecha y operador. Solo quien hizo la revisión podrá marcarla; usar datos autorizados. El escaneo de QR queda sujeto a confirmación del formato solicitado.
- [ ] C conecta formulario de cliente, selector de servicios, cantidades, desglose, emisión, saldo y comprobante. Usar textContent para datos variables, manejar errores y conservar la clave al reintentar.
- [ ] D prepara infra para lab, database/dynamodb.json y documentación de claves. API HTTPS, JWT, RDS privado, cifrado y TLS, permisos restringidos y secretos fuera de Git. Configurar 128–256 MB en Lambda, RDS micro hasta 20 GB y DynamoDB bajo demanda. Documentar inicio, parada, rotación de credenciales y gasto.
- [ ] D (Martín) comprueba el despliegue y entrega a A (Mauricio) la URL del panel con ambas RDS disponibles. A prepara y demuestra la emisión, el pago parcial con reintento, la sesión válida/anónima, el rechazo de acceso a una factura ajena y el auditor sin escritura. A registra entorno, folio ficticio, saldos y resultados sin tokens ni RFC reales en docs/evidencias. C prueba el doble clic en el panel.
- [ ] Cada uno explica un segmento de su PR y sigue una petición hasta la capa vecina. Ensayar la demo desde un navegador nuevo antes de la revisión.
## Cierre · 24–26
- [ ] A y B completan los cinco procedimientos restantes e integran permisos y transacciones. Una cancelación conserva historial y evita doble reversión; el cierre evita duplicados.
- [ ] C conecta pantallas para las cinco operaciones restantes. D y B completan auditoría con eventos pendientes en RDS y entrega idempotente a DynamoDB. Probar reintento tras fallo.
- [ ] D mide latencia p95, errores y conexiones con carga moderada; A revisa planes de consulta. Probar paginación, límites, cambio histórico de tarifa, registros de errores sin datos sensibles y visualización literal de texto.
- [ ] Equipo coteja rúbrica: modelo 30 %, AWS 25 %, lógica 20 %, seguridad 15 %, interfaz/documentación/Git 10 %. Entregar DER, diagramas C4 y AWS, OpenAPI, DDL/DML, SP, esquema DynamoDB, código y README de despliegue y pruebas.
- [ ] Otra persona despliega siguiendo README. Arrancar RDS con tiempo el día 26, verificar los diez flujos y etiquetar la versión entregada. Ensayar preguntas cruzadas y repetir las que fallen.
