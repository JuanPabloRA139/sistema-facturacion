-- Ejecutar exclusivamente en la instancia del directorio.
CREATE TABLE IF NOT EXISTS usuarios_roles (
    usuario_id text PRIMARY KEY,
    rol text NOT NULL CHECK (rol IN ('operador','administrador','auditor'))
);
CREATE TABLE IF NOT EXISTS migraciones (nombre text PRIMARY KEY);
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
