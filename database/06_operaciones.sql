BEGIN;
CREATE TABLE IF NOT EXISTS reversiones (
    folio bigint PRIMARY KEY REFERENCES facturas,
    fecha date NOT NULL DEFAULT CURRENT_DATE,
    actor text NOT NULL REFERENCES usuarios_roles,
    motivo text NOT NULL,
    importe numeric(16,2) NOT NULL CHECK (importe <= 0)
);
CREATE TABLE IF NOT EXISTS cierres (
    inicio date NOT NULL, fin date NOT NULL, neto numeric(18,2) NOT NULL,
    actor text NOT NULL REFERENCES usuarios_roles, PRIMARY KEY (inicio,fin)
);
CREATE TABLE IF NOT EXISTS auditoria_tarifas (
    evento bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    servicio_id integer NOT NULL REFERENCES servicios,
    actor text NOT NULL REFERENCES usuarios_roles,
    creado timestamptz NOT NULL DEFAULT now(),
    anterior numeric(12,2) NOT NULL, nuevo numeric(12,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS facturas_usuario_folio ON facturas(usuario_id,folio);
CREATE INDEX IF NOT EXISTS facturas_fecha ON facturas(fecha);
CREATE INDEX IF NOT EXISTS reversiones_fecha ON reversiones(fecha);

COMMIT;
