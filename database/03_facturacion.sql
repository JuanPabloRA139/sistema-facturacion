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
COMMIT;
