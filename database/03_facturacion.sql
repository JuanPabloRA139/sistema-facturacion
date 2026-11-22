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
COMMIT;
