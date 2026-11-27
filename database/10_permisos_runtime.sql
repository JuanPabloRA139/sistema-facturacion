-- Ejecutar como propietario de la base, en la misma transacción que el esquema.
-- El usuario de la API puede ejecutar operaciones, pero no editar los
-- movimientos financieros ni añadir eventos de auditoría directamente.
DO $$
DECLARE
    propietario pg_roles%ROWTYPE;
    marca text := 'facturacion-servicios:propietario-operaciones:v1';
BEGIN
    SELECT * INTO propietario FROM pg_roles WHERE rolname='facturacion_operaciones';
    IF NOT FOUND THEN
        CREATE ROLE facturacion_operaciones NOLOGIN;
        EXECUTE format('COMMENT ON ROLE facturacion_operaciones IS %L', marca);
    ELSIF propietario.rolcanlogin OR propietario.rolsuper OR propietario.rolcreaterole
       OR propietario.rolcreatedb OR propietario.rolreplication OR propietario.rolbypassrls
       OR EXISTS (SELECT 1 FROM pg_auth_members WHERE member=propietario.oid)
       OR pg_has_role('facturacion_app',propietario.oid,'MEMBER')
       OR shobj_description(propietario.oid,'pg_authid') IS DISTINCT FROM marca THEN
        RAISE EXCEPTION 'El propietario SQL preexistente no cumple el contrato de seguridad';
    END IF;
END; $$;
GRANT facturacion_operaciones TO CURRENT_USER WITH INHERIT TRUE;
GRANT facturacion_operaciones TO CURRENT_USER WITH SET TRUE;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO facturacion_app, facturacion_operaciones;

-- Retirar los permisos de tabla, columna y secuencia de la versión anterior.
REVOKE ALL PRIVILEGES ON usuarios_roles,clientes,servicios,caracteristicas,facturas,
    detalle_factura,pagos,impuestos_historico,series_factura,reversiones,cierres,
    eventos_pendientes,auditoria_tarifas,caracteristicas_servicio FROM facturacion_app;
REVOKE UPDATE(ultimo) ON series_factura FROM facturacion_app;
REVOKE UPDATE(estado) ON facturas FROM facturacion_app;
REVOKE UPDATE(precio) ON servicios FROM facturacion_app;
REVOKE UPDATE(enviado) ON eventos_pendientes FROM facturacion_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM facturacion_app;
REVOKE EXECUTE ON ALL ROUTINES IN SCHEMA public FROM PUBLIC, facturacion_app;

-- Lecturas y escrituras directas usadas realmente por el adaptador de la API.
GRANT SELECT ON usuarios_roles,servicios,caracteristicas,impuestos_historico,
    eventos_pendientes TO facturacion_app;
GRANT SELECT(cliente_id,nombre,responsable), INSERT(responsable,nombre,rfc)
    ON clientes TO facturacion_app;
GRANT SELECT(folio,fecha,total,estado,usuario_id) ON facturas TO facturacion_app;
GRANT USAGE ON SEQUENCE clientes_cliente_id_seq TO facturacion_app;
GRANT UPDATE(enviado) ON eventos_pendientes TO facturacion_app;

-- Propietario sin inicio de sesión, sin permisos de administración de la base.
GRANT SELECT ON usuarios_roles,clientes,servicios,facturas,detalle_factura,pagos,
    impuestos_historico,series_factura,reversiones,cierres TO facturacion_operaciones;
GRANT INSERT ON facturas,detalle_factura,pagos,reversiones,cierres,eventos_pendientes,
    auditoria_tarifas,caracteristicas_servicio TO facturacion_operaciones;
GRANT UPDATE(ultimo) ON series_factura TO facturacion_operaciones;
GRANT UPDATE(estado) ON facturas TO facturacion_operaciones;
GRANT UPDATE(precio) ON servicios TO facturacion_operaciones;
GRANT USAGE ON SEQUENCE pagos_pago_id_seq,auditoria_tarifas_evento_seq,
    eventos_pendientes_evento_id_seq TO facturacion_operaciones;
GRANT EXECUTE ON PROCEDURE aplicar_descuento(numeric,integer,numeric),
    calcular_importes(numeric,date,numeric,numeric,numeric) TO facturacion_operaciones;

-- PostgreSQL exige CREATE en el esquema para transferir estos objetos.
-- Se retira en esta misma transacción, antes de hacer visibles los cambios.
GRANT CREATE ON SCHEMA public TO facturacion_operaciones;
DO $$
DECLARE firma text;
BEGIN
    FOREACH firma IN ARRAY ARRAY[
        'public.emitir_factura(text,bigint,uuid,jsonb,bigint)',
        'public.registrar_pago(text,bigint,text,numeric,boolean,numeric)',
        'public.cancelar_factura(text,bigint,text)',
        'public.cerrar_periodo(text,date,boolean,numeric)',
        'public.antiguedad_saldos(text,jsonb)',
        'public.generar_comprobante(text,bigint,jsonb)',
        'public.asignar_caracteristicas(text,integer[],integer[])',
        'public.cambiar_tarifa(text,integer,numeric)'
    ] LOOP
        -- Lista fija del proyecto. Ningún dato de una solicitud entra al DDL.
        EXECUTE 'ALTER PROCEDURE ' || firma || ' OWNER TO facturacion_operaciones';
        EXECUTE 'ALTER PROCEDURE ' || firma || ' SET search_path = pg_catalog, public, pg_temp';
        EXECUTE 'ALTER PROCEDURE ' || firma || ' SECURITY DEFINER';
        EXECUTE 'GRANT EXECUTE ON PROCEDURE ' || firma || ' TO facturacion_app';
    END LOOP;
END; $$;
REVOKE CREATE ON SCHEMA public FROM facturacion_operaciones;
