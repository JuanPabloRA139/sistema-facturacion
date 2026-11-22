BEGIN;
CREATE TABLE IF NOT EXISTS usuarios_roles (
    usuario_id text PRIMARY KEY,
    rol text NOT NULL CHECK (rol IN ('operador','administrador','auditor'))
);
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    responsable text NOT NULL REFERENCES usuarios_roles,
    nombre text NOT NULL,
    rfc varchar(13) NOT NULL,
    UNIQUE (responsable,rfc)
);
CREATE TABLE IF NOT EXISTS impuestos_historico (
    desde date PRIMARY KEY,
    iva numeric(5,4) NOT NULL CHECK (iva BETWEEN 0 AND 1),
    retencion numeric(5,4) NOT NULL CHECK (retencion BETWEEN 0 AND 1)
);
INSERT INTO impuestos_historico VALUES ('2000-01-01',0.16,0.04) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS series_factura (
    serie text PRIMARY KEY,
    ultimo bigint NOT NULL CHECK (ultimo >= 0)
);
INSERT INTO series_factura VALUES ('A',0) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS facturas (
    folio bigint PRIMARY KEY,
    usuario_id text NOT NULL REFERENCES usuarios_roles,
    cliente_id bigint NOT NULL REFERENCES clientes,
    clave uuid NOT NULL,
    conceptos_solicitados jsonb NOT NULL,
    fecha date NOT NULL DEFAULT CURRENT_DATE,
    vence date NOT NULL DEFAULT (CURRENT_DATE+30),
    estado text NOT NULL DEFAULT 'emitida' CHECK (estado IN ('emitida','parcial','pagada','cancelada')),
    subtotal numeric(16,2) NOT NULL,
    descuento numeric(16,2) NOT NULL,
    iva numeric(16,2) NOT NULL,
    retencion numeric(16,2) NOT NULL,
    total numeric(16,2) NOT NULL,
    UNIQUE (usuario_id,clave)
);
CREATE TABLE IF NOT EXISTS detalle_factura (
    folio bigint REFERENCES facturas,
    renglon integer NOT NULL,
    servicio_id integer NOT NULL REFERENCES servicios,
    descripcion text NOT NULL,
    precio numeric(12,2) NOT NULL,
    cantidad integer NOT NULL CHECK (cantidad BETWEEN 1 AND 999),
    PRIMARY KEY (folio,renglon)
);
CREATE TABLE IF NOT EXISTS pagos (
    pago_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    folio bigint NOT NULL REFERENCES facturas,
    referencia text NOT NULL,
    importe numeric(16,2) NOT NULL CHECK (importe>0),
    UNIQUE (folio,referencia)
);
COMMIT;
