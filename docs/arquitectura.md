# Arquitectura del Sistema de Facturación y Servicios

## Contexto C4

```mermaid
flowchart TD
    Op["Operador"] -->|Emite y cobra sus facturas| Sistema["Sistema de facturación y servicios"]
    Ad["Administrador"] -->|Mantiene tarifas y efectúa cierres| Sistema
    Au["Auditor"] -->|Consulta comprobantes y cartera| Sistema
    Sistema -->|Delegación del inicio de sesión| IdP["Proveedor de identidad · Amazon Cognito"]
```

Los comprobantes del proyecto son estructuras JSON de demostración académica. El alta de cliente valida el formato y la fecha del RFC. Cognito autentica a la persona y el backend consulta su rol en el directorio de la aplicación.

## Contenedores C4 y despliegue en AWS

```mermaid
flowchart TD
    U["Navegador · panel HTML y JavaScript"] -->|Inicio de sesión con PKCE| Cog["Cognito"]
    U -->|HTTPS| G["HTTP API · API Gateway"]
    G -->|GET del panel y recursos| Web["Lambda Web"]
    G -->|POST con autorizador JWT| Api["Lambda Api · Python"]
    Api -->|Rol del usuario| Dir["RDS PostgreSQL · identidades"]
    Api -->|Casos de uso y procedimientos| BD["RDS PostgreSQL · facturación"]
    Api -->|Eventos y consulta del historial| Audit["DynamoDB · auditoría"]
    Api -->|Credenciales de aplicación| SM["Secrets Manager"]
    Des["Operador del despliegue"] -->|Invocación administrativa AWS| Admin["Lambda Admin"]
    Admin -->|Esquema y roles| BD
    Admin -->|Directorio| Dir
    Admin -->|Credenciales de inicialización| SM
```

El operador del despliegue se autentica en AWS. Lambda Admin se invoca mediante AWS y carece de ruta en la API pública de la pila. Las Lambdas Api y Admin están en la VPC y llegan a PostgreSQL en el puerto 5432. La plantilla usa dos subredes privadas, un endpoint de interfaz para secretos y uno de gateway para DynamoDB. El panel llama a la API con un token de acceso. La API compara el rol del directorio con su copia operativa antes de ejecutar el caso de uso. La configuración efectiva del laboratorio y sus permisos se verifican por separado. [Operación en AWS](conexion-aws.md)

### Recorrido de un pago

1. El panel confirma folio, referencia e importe en centavos y envía `POST /api/pago`.
2. API Gateway valida el JWT. La Lambda toma el identificador de usuario del token y un bloqueo compartido por usuario en facturación. Lee el rol con la cuenta de consulta del directorio y verifica la copia operativa. Una discrepancia interrumpe la operación.
3. `backend/servicios.py` valida la entrada. `backend/rds.py` pasa valores parametrizados al procedimiento `registrar_pago`, que comprueba acceso, saldo y duplicados. Un disparador escribe el evento pendiente en la misma transacción.
4. La API confirma la transacción e intenta exportar un lote a DynamoDB antes de devolver el comprobante. Si el envío falla, el evento sigue pendiente hasta una operación posterior.

La Lambda Admin toma un bloqueo exclusivo al modificar el rol de un usuario. Si el directorio y la copia operativa quedan distintos tras un fallo entre sus dos transacciones, una persona autorizada debe verificar y reconciliar la asignación. [Recuperación de altas](seguridad-despliegue.md)

## DER de facturación · 14 tablas

Los diagramas agrupan las tablas de una misma RDS. Una entidad puede reaparecer para mostrar sus relaciones en otro grupo. Las marcas PK y FK identifican claves primarias y foráneas del DDL. Cuando varias columnas llevan PK, forman una sola clave compuesta.

### Clientes, facturas y cobros

```mermaid
erDiagram
    usuarios_roles ||--o{ clientes : administra
    usuarios_roles ||--o{ facturas : emite
    clientes ||--o{ facturas : recibe
    facturas ||--|{ detalle_factura : contiene
    servicios ||--o{ detalle_factura : describe
    facturas ||--o{ pagos : recibe
    usuarios_roles {
        text usuario_id PK
        text rol
    }
    clientes {
        bigint cliente_id PK
        text responsable FK
        text nombre
        varchar rfc
    }
    facturas {
        bigint folio PK
        text usuario_id FK
        bigint cliente_id FK
        uuid clave
        jsonb conceptos_solicitados
        date fecha
        date vence
        text estado
        numeric subtotal
        numeric descuento
        numeric iva
        numeric retencion
        numeric total
    }
    detalle_factura {
        bigint folio PK,FK
        integer renglon PK
        integer servicio_id FK
        text descripcion
        numeric precio
        integer cantidad
    }
    servicios {
        integer servicio_id PK
        varchar codigo UK
        varchar nombre
        numeric precio
    }
    pagos {
        bigint pago_id PK
        bigint folio FK
        text referencia
        numeric importe
    }
```

El esquema impone unicidad en `clientes(responsable,rfc)`, `facturas(usuario_id,clave)` y `pagos(folio,referencia)`. El procedimiento de emisión exige entre uno y treinta conceptos por solicitud. El detalle conserva el precio y la descripción vigentes en la emisión.

### Catálogo, reversiones y cierres

```mermaid
erDiagram
    servicios ||--o{ caracteristicas_servicio : configura
    caracteristicas ||--o{ caracteristicas_servicio : asigna
    servicios ||--o{ auditoria_tarifas : registra
    usuarios_roles ||--o{ auditoria_tarifas : modifica
    facturas ||--o| reversiones : revierte
    usuarios_roles ||--o{ reversiones : autoriza
    usuarios_roles ||--o{ cierres : efectua
    caracteristicas {
        integer caracteristica_id PK
        varchar codigo UK
        varchar nombre
    }
    caracteristicas_servicio {
        integer servicio_id PK,FK
        integer caracteristica_id PK,FK
    }
    auditoria_tarifas {
        bigint evento PK
        integer servicio_id FK
        text actor FK
        timestamptz creado
        numeric anterior
        numeric nuevo
    }
    reversiones {
        bigint folio PK,FK
        date fecha
        text actor FK
        text motivo
        numeric importe
    }
    cierres {
        date inicio PK
        date fin PK
        numeric neto
        text actor FK
    }
```

### Folios, vigencias y exportación de eventos

```mermaid
erDiagram
    series_factura {
        text serie PK
        bigint ultimo
    }
    impuestos_historico {
        date desde PK
        numeric iva
        numeric retencion
    }
    eventos_pendientes {
        bigint evento_id PK
        timestamptz fecha
        text entidad
        text accion
        text actor
        jsonb detalle
        boolean enviado
    }
```

Estas tres tablas son independientes en el DDL. `emitir_factura` bloquea la fila de la serie al reservar el folio. `calcular_importes` lee la tasa vigente al emitir. Los disparadores en facturas, pagos, reversiones y auditoría de tarifas crean entradas en `eventos_pendientes`. El índice parcial de eventos pendientes acelera la selección de lotes por exportar.

## DER de identidades · 2 tablas

```mermaid
erDiagram
    usuarios_roles {
        text usuario_id PK
        text rol
    }
    migraciones {
        text nombre PK
    }
```

El directorio persiste el identificador de Cognito y el rol. `migraciones` registra la inicialización del directorio. La tabla homónima `usuarios_roles` en facturación permite las FK locales. La aplicación verifica la coincidencia entre ambas instancias para cada operación.

## Modelo de DynamoDB

La tabla de auditoría usa `entidad` como clave de partición y `evento` como clave de orden. El valor de evento combina la fecha UTC y el identificador PostgreSQL para que un reintento use la misma clave. El índice secundario `historial` usa `listado` y `evento` y devuelve hasta los 100 eventos recientes. [Esquema DynamoDB](../database/dynamodb.json)

## Preguntas para el examen
- Datos. Explica la diferencia entre el folio y la clave de reintento. Sigue el bloqueo de serie y el índice único en emitir_factura.
- Backend. Sigue el sub de Cognito desde API Gateway hasta el filtro de permisos en backend/identidades.py y backend/servicios.py. Explica quién decide si un pago es duplicado.
- Frontend. Sigue un renglón desde el formulario hasta el comprobante e identifica dónde se aplica textContent y dónde se valida el RFC otra vez.
- AWS. Dibuja los dos recorridos, HTML público y operaciones con JWT. Explica cómo se recupera un evento si falla DynamoDB después de guardar la factura.
