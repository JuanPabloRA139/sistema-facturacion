BEGIN;
DO $$
DECLARE
    operador text := 'op-' || txid_current();
    admin text := 'adm-' || txid_current();
    cliente bigint; sid integer; cid integer; lineas jsonb; folio bigint; otro bigint;
    respuesta jsonb; repetido boolean; saldo numeric;
BEGIN
    INSERT INTO usuarios_roles VALUES (operador,'operador'),(admin,'administrador');
    INSERT INTO clientes(responsable,nombre,rfc) VALUES(operador,'Demo','XAXX010101000') RETURNING cliente_id INTO cliente;
    SELECT servicio_id INTO STRICT sid FROM servicios WHERE codigo='S1';
    SELECT caracteristica_id INTO STRICT cid FROM caracteristicas WHERE codigo='C2';
    lineas := jsonb_build_array(jsonb_build_object('servicio',sid,'cantidad',1));
    CALL emitir_factura(operador,cliente,'10000000-0000-4000-8000-000000000001',lineas,folio);
    CALL registrar_pago(operador,folio,'DEMO-1',50,repetido,saldo);
    IF repetido OR saldo<>67.60 THEN RAISE EXCEPTION 'Falló pago parcial'; END IF;
    CALL registrar_pago(operador,folio,'DEMO-1',50,repetido,saldo);
    IF NOT repetido OR saldo<>67.60 THEN RAISE EXCEPTION 'Falló reintento de pago'; END IF;
    BEGIN
        CALL registrar_pago(operador,folio,'DEMO-1',51,repetido,saldo);
        RAISE EXCEPTION 'Se admitió un importe distinto con la misma referencia';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'Referencia utilizada con otro importe' THEN RAISE; END IF;
    END;
    INSERT INTO usuarios_roles VALUES ('otro-' || operador,'operador');
    BEGIN
        CALL generar_comprobante('otro-' || operador,folio,respuesta);
        RAISE EXCEPTION 'Otro operador recibió un comprobante ajeno';
    EXCEPTION WHEN no_data_found THEN NULL;
    END;
    CALL antiguedad_saldos(operador,respuesta);
    IF NOT respuesta @> jsonb_build_array(jsonb_build_object('folio',folio,'saldo',67.60)) THEN RAISE EXCEPTION 'Falló reporte'; END IF;
    CALL cambiar_tarifa(admin,sid,220);
    IF NOT EXISTS (SELECT 1 FROM auditoria_tarifas WHERE servicio_id=sid AND nuevo=220 AND anterior=105)
       THEN RAISE EXCEPTION 'Falló auditoría'; END IF;
    CALL generar_comprobante(operador,folio,respuesta);
    IF (respuesta->>'total')::numeric<>117.60 THEN RAISE EXCEPTION 'La factura cambió de precio'; END IF;
    CALL asignar_caracteristicas(admin,ARRAY[sid],ARRAY[cid]);
    IF NOT EXISTS (SELECT 1 FROM caracteristicas_servicio WHERE servicio_id=sid AND caracteristica_id=cid)
       THEN RAISE EXCEPTION 'Falló asignación'; END IF;
    CALL emitir_factura(operador,cliente,'10000000-0000-4000-8000-000000000002',lineas,otro);
    CALL cancelar_factura(admin,otro,'Corrección de prueba');
    CALL cancelar_factura(admin,otro,'Corrección de prueba');
    IF NOT EXISTS (SELECT 1 FROM reversiones r WHERE r.folio=otro AND importe=-246.40)
       THEN RAISE EXCEPTION 'Falló la reversión'; END IF;
    CALL cerrar_periodo(admin,CURRENT_DATE-1,false,saldo);
    IF saldo IS NULL THEN RAISE EXCEPTION 'Falló cierre'; END IF;
    -- La fecha de una transacción iniciada antes de medianoche puede ser la
    -- de ayer al confirmar. Un movimiento tardío no debe alterar un cierre.
    BEGIN
        INSERT INTO facturas(folio,usuario_id,cliente_id,clave,conceptos_solicitados,fecha,
                             subtotal,descuento,iva,retencion,total)
        VALUES(-txid_current(),operador,cliente,'10000000-0000-4000-8000-000000000003',
               lineas,CURRENT_DATE-1,105,0,16.80,4.20,117.60);
        RAISE EXCEPTION 'Se admitió una factura de un periodo cerrado';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'El periodo del movimiento ya está cerrado' THEN RAISE; END IF;
    END;
    CALL cerrar_periodo(admin,(date_trunc('month',CURRENT_DATE) - interval '1 month')::date,true,saldo);
    BEGIN
        INSERT INTO reversiones(folio,fecha,actor,motivo,importe)
        VALUES(folio,date_trunc('month',CURRENT_DATE)::date-1,admin,'Regresión de cierre mensual',-1);
        RAISE EXCEPTION 'Se admitió una reversión de un mes cerrado';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM <> 'El periodo del movimiento ya está cerrado' THEN RAISE; END IF;
    END;
END; $$;
ROLLBACK;
