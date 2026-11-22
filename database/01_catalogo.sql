BEGIN;
CREATE TABLE IF NOT EXISTS servicios (
    servicio_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo varchar(12) NOT NULL UNIQUE,
    nombre varchar(100) NOT NULL,
    precio numeric(12,2) NOT NULL CHECK (precio > 0)
);
CREATE TABLE IF NOT EXISTS caracteristicas (
    caracteristica_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo varchar(12) NOT NULL UNIQUE,
    nombre varchar(100) NOT NULL
);
CREATE TABLE IF NOT EXISTS caracteristicas_servicio (
    servicio_id integer REFERENCES servicios ON DELETE RESTRICT,
    caracteristica_id integer REFERENCES caracteristicas ON DELETE RESTRICT,
    PRIMARY KEY (servicio_id, caracteristica_id)
);
COMMIT;
