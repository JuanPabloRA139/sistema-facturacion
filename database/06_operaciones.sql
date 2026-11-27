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
CREATE INDEX IF NOT EXISTS saldos_vencimiento ON facturas(vence,folio) WHERE estado IN ('emitida','parcial');

-- Las emisiones y reversiones pueden coincidir con el cambio de día. El cierre
-- debe ver las escrituras ya aceptadas y rechazar movimientos tardíos.
CREATE OR REPLACE FUNCTION comprobar_periodo_abierto() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock_shared(19041, 1);
    IF EXISTS (
        SELECT 1 FROM cierres
        WHERE inicio IN (NEW.fecha, date_trunc('month', NEW.fecha)::date)
          AND NEW.fecha < fin
    ) THEN
        RAISE EXCEPTION 'El periodo del movimiento ya está cerrado';
    END IF;
    RETURN NEW;
END; $$;
CREATE OR REPLACE TRIGGER verificar_periodo_factura BEFORE INSERT ON facturas
    FOR EACH ROW EXECUTE FUNCTION comprobar_periodo_abierto();
CREATE OR REPLACE TRIGGER verificar_periodo_reversion BEFORE INSERT ON reversiones
    FOR EACH ROW EXECUTE FUNCTION comprobar_periodo_abierto();

CREATE OR REPLACE PROCEDURE registrar_pago(
    IN actor text, IN p_folio bigint, IN p_referencia text, IN p_importe numeric,
    INOUT repetido boolean, INOUT saldo numeric)
LANGUAGE plpgsql AS $$
DECLARE
    f facturas%ROWTYPE;
    previo numeric;
BEGIN
    IF p_importe IS NULL OR NOT (p_importe>0 AND p_importe<100000000000000 AND p_importe=round(p_importe,2))
       OR coalesce(length(trim(p_referencia)),0) NOT BETWEEN 1 AND 64 THEN
        RAISE EXCEPTION 'Importe o referencia inválidos';
    END IF;
    SELECT fac.* INTO STRICT f FROM facturas fac JOIN usuarios_roles u ON u.usuario_id=actor
      WHERE fac.folio=p_folio AND (u.rol='administrador' OR (u.rol='operador' AND fac.usuario_id=actor))
      FOR UPDATE OF fac;
    SELECT f.total-coalesce(sum(p.importe),0) INTO saldo FROM pagos p WHERE p.folio=p_folio;
    SELECT p.importe INTO previo FROM pagos p WHERE p.folio=p_folio AND p.referencia=trim(p_referencia);
    repetido := FOUND;
    IF repetido THEN
        IF previo<>p_importe THEN RAISE EXCEPTION 'Referencia utilizada con otro importe'; END IF;
        RETURN;
    END IF;
    IF f.estado='cancelada' OR p_importe>saldo THEN RAISE EXCEPTION 'Pago incompatible con el saldo'; END IF;
    INSERT INTO pagos(folio,referencia,importe) VALUES (p_folio,trim(p_referencia),p_importe);
    saldo := saldo-p_importe;
    UPDATE facturas SET estado=CASE WHEN saldo=0 THEN 'pagada' ELSE 'parcial' END WHERE folio=p_folio;
END; $$;

CREATE OR REPLACE PROCEDURE cancelar_factura(IN actor text, IN p_folio bigint, IN motivo text)
LANGUAGE plpgsql AS $$
DECLARE f facturas%ROWTYPE;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id=actor AND rol='administrador')
       THEN RAISE EXCEPTION 'Acceso denegado'; END IF;
    IF coalesce(length(trim(motivo)),0) NOT BETWEEN 1 AND 160 THEN RAISE EXCEPTION 'Motivo inválido'; END IF;
    SELECT * INTO STRICT f FROM facturas WHERE folio=p_folio FOR UPDATE;
    IF f.estado='cancelada' THEN RETURN; END IF;
    IF EXISTS (SELECT 1 FROM pagos WHERE folio=p_folio) THEN RAISE EXCEPTION 'Hay pagos aplicados'; END IF;
    INSERT INTO reversiones(folio,actor,motivo,importe) VALUES (p_folio,actor,trim(motivo),-f.total);
    UPDATE facturas SET estado='cancelada' WHERE folio=p_folio;
END; $$;

CREATE OR REPLACE PROCEDURE cerrar_periodo(IN actor text, IN inicio_periodo date, IN mensual boolean, INOUT resultado numeric)
LANGUAGE plpgsql AS $$
DECLARE fin_periodo date;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id=actor AND rol='administrador')
       THEN RAISE EXCEPTION 'Acceso denegado'; END IF;
    IF inicio_periodo IS NULL OR mensual IS NULL OR (mensual AND extract(day FROM inicio_periodo)<>1)
       THEN RAISE EXCEPTION 'Inicio de periodo inválido'; END IF;
    fin_periodo := CASE WHEN mensual THEN (inicio_periodo+interval '1 month')::date ELSE inicio_periodo+1 END;
    IF fin_periodo>CURRENT_DATE THEN RAISE EXCEPTION 'Periodo en curso'; END IF;
    PERFORM pg_advisory_xact_lock(19041, 1);
    INSERT INTO cierres(inicio,fin,neto,actor)
    SELECT inicio_periodo,fin_periodo,coalesce(sum(m.importe),0),actor FROM (
        SELECT total AS importe FROM facturas WHERE fecha>=inicio_periodo AND fecha<fin_periodo
        UNION ALL SELECT importe FROM reversiones WHERE fecha>=inicio_periodo AND fecha<fin_periodo
    ) m ON CONFLICT (inicio,fin) DO NOTHING;
    SELECT neto INTO STRICT resultado FROM cierres WHERE inicio=inicio_periodo AND fin=fin_periodo;
END; $$;

CREATE OR REPLACE PROCEDURE antiguedad_saldos(IN actor text, INOUT resultado jsonb)
LANGUAGE plpgsql AS $$
DECLARE
    -- El segundo argumento es NULL en las llamadas históricas. En modo página
    -- proporciona el cursor y devuelve una fila extra para detectar la siguiente.
    limite integer := 200;
    desde_fecha date := '-infinity';
    desde_folio bigint := 0;
BEGIN
    IF resultado @> '{"paginado":true}'::jsonb THEN
        limite := 201;
        IF jsonb_typeof(resultado->'despues_de') = 'object' THEN
            desde_fecha := (resultado->'despues_de'->>'vence')::date;
            desde_folio := (resultado->'despues_de'->>'folio')::bigint;
        END IF;
    END IF;
    SELECT coalesce(jsonb_agg(to_jsonb(listado) ORDER BY vence,folio),'[]') INTO resultado FROM (
        SELECT f.folio,f.vence,greatest(CURRENT_DATE-f.vence,0) AS dias_vencidos,
               f.total-coalesce((SELECT sum(p.importe) FROM pagos p WHERE p.folio=f.folio),0) AS saldo
        FROM facturas f JOIN usuarios_roles u ON u.usuario_id=actor
        WHERE (u.rol IN ('auditor','administrador') OR f.usuario_id=actor)
          AND f.estado IN ('emitida','parcial')
          AND (f.vence,f.folio) > (desde_fecha,desde_folio)
        ORDER BY f.vence,f.folio LIMIT limite
    ) listado;
END; $$;

CREATE OR REPLACE PROCEDURE generar_comprobante(IN actor text, IN p_folio bigint, INOUT resultado jsonb)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT jsonb_build_object('folio',f.folio,'fecha',f.fecha,'cliente',c.nombre,'rfc',c.rfc,
        'estado',f.estado,'subtotal',f.subtotal,'descuento',f.descuento,'iva',f.iva,'retencion',f.retencion,
        'total',f.total,'pagado',p.suma,'saldo',CASE WHEN f.estado='cancelada' THEN 0 ELSE f.total-p.suma END,
        'conceptos',(SELECT jsonb_agg(jsonb_build_object('nombre',d.descripcion,'cantidad',d.cantidad,
                    'precio',d.precio) ORDER BY d.renglon) FROM detalle_factura d WHERE d.folio=f.folio))
      INTO STRICT resultado
      FROM facturas f JOIN clientes c USING(cliente_id) JOIN usuarios_roles u ON u.usuario_id=actor
      CROSS JOIN LATERAL (SELECT coalesce(sum(importe),0) AS suma FROM pagos WHERE folio=f.folio) p
      WHERE f.folio=p_folio AND (u.rol IN ('auditor','administrador') OR f.usuario_id=actor);
END; $$;

CREATE OR REPLACE PROCEDURE asignar_caracteristicas(IN actor text, IN ids_servicio integer[], IN ids_caracteristica integer[])
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id=actor AND rol='administrador')
       THEN RAISE EXCEPTION 'Acceso denegado'; END IF;
    IF coalesce(cardinality(ids_servicio),0) NOT BETWEEN 1 AND 100 OR
       coalesce(cardinality(ids_caracteristica),0) NOT BETWEEN 1 AND 50 THEN RAISE EXCEPTION 'Lote inválido'; END IF;
    INSERT INTO caracteristicas_servicio(servicio_id,caracteristica_id)
    SELECT s.id,c.id FROM unnest(ids_servicio) s(id) CROSS JOIN unnest(ids_caracteristica) c(id)
    ON CONFLICT DO NOTHING;
END; $$;

CREATE OR REPLACE PROCEDURE cambiar_tarifa(IN actor text, IN p_servicio integer, IN precio_nuevo numeric)
LANGUAGE plpgsql AS $$
DECLARE precio_anterior numeric;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuarios_roles WHERE usuario_id=actor AND rol='administrador')
       THEN RAISE EXCEPTION 'Acceso denegado'; END IF;
    IF precio_nuevo IS NULL OR NOT (precio_nuevo>0 AND precio_nuevo<10000000000 AND precio_nuevo=round(precio_nuevo,2))
       THEN RAISE EXCEPTION 'Precio inválido'; END IF;
    SELECT precio INTO STRICT precio_anterior FROM servicios WHERE servicio_id=p_servicio FOR UPDATE;
    IF precio_anterior=precio_nuevo THEN RETURN; END IF;
    UPDATE servicios SET precio=precio_nuevo WHERE servicio_id=p_servicio;
    INSERT INTO auditoria_tarifas(servicio_id,actor,anterior,nuevo) VALUES(p_servicio,actor,precio_anterior,precio_nuevo);
END; $$;
COMMIT;
