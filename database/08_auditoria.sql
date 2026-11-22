BEGIN;
CREATE TABLE IF NOT EXISTS eventos_pendientes (
    evento_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fecha timestamptz NOT NULL DEFAULT clock_timestamp(),
    entidad text NOT NULL, accion text NOT NULL, actor text NOT NULL,
    detalle jsonb NOT NULL DEFAULT '{}', enviado boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS eventos_por_enviar ON eventos_pendientes(evento_id) WHERE NOT enviado;
CREATE OR REPLACE FUNCTION preparar_evento() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    sujeto text := current_setting('facturacion.actor',true);
    recurso text;
    datos jsonb := '{}';
BEGIN
    IF TG_TABLE_NAME='auditoria_tarifas' THEN
        recurso := 'SERVICIO#'||NEW.servicio_id;
        datos := jsonb_build_object('anterior',NEW.anterior::text,'nuevo',NEW.nuevo::text);
        sujeto := NEW.actor;
    ELSE
        recurso := 'FACTURA#'||NEW.folio;
    END IF;
    INSERT INTO eventos_pendientes(entidad,accion,actor,detalle)
    VALUES(recurso,TG_ARGV[0],coalesce(nullif(sujeto,''),current_user),datos);
    RETURN NEW;
END; $$;
CREATE OR REPLACE TRIGGER auditar_emision AFTER INSERT ON facturas
 FOR EACH ROW EXECUTE FUNCTION preparar_evento('emisión');
CREATE OR REPLACE TRIGGER auditar_pago AFTER INSERT ON pagos
 FOR EACH ROW EXECUTE FUNCTION preparar_evento('pago');
CREATE OR REPLACE TRIGGER auditar_cancelacion AFTER INSERT ON reversiones
 FOR EACH ROW EXECUTE FUNCTION preparar_evento('cancelación');
CREATE OR REPLACE TRIGGER auditar_tarifa AFTER INSERT ON auditoria_tarifas
 FOR EACH ROW EXECUTE FUNCTION preparar_evento('tarifa');
COMMIT;
