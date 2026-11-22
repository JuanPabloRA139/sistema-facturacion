BEGIN;
CREATE OR REPLACE PROCEDURE aplicar_descuento(IN subtotal numeric, IN unidades integer, INOUT descuento numeric)
LANGUAGE plpgsql AS $$
BEGIN
    descuento := CASE WHEN unidades >= 10 THEN round(subtotal * 0.05,2) ELSE 0 END;
END;
$$;

CREATE OR REPLACE PROCEDURE calcular_importes(IN base numeric, IN fecha date,
    INOUT iva numeric, INOUT retencion numeric, INOUT total numeric)
LANGUAGE plpgsql AS $$
DECLARE
    tasas impuestos_historico%ROWTYPE;
BEGIN
    SELECT * INTO STRICT tasas FROM impuestos_historico
      WHERE desde <= fecha ORDER BY desde DESC LIMIT 1;
    iva := round(base * tasas.iva,2);
    retencion := round(base * tasas.retencion,2);
    total := base + iva - retencion;
END;
$$;

CREATE OR REPLACE PROCEDURE emitir_factura(IN actor text, IN cliente bigint, IN solicitud uuid,
    IN conceptos jsonb, INOUT resultado bigint)
LANGUAGE plpgsql AS $$
DECLARE
    anterior facturas%ROWTYPE;
    lineas jsonb;
    subtotal_calc numeric;
    descuento_calc numeric;
    unidades integer;
    iva_calc numeric;
    ret_calc numeric;
    total_calc numeric;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM usuarios_roles u JOIN clientes c ON c.cliente_id=cliente
        WHERE u.usuario_id=actor AND (u.rol='administrador' OR
              (u.rol='operador' AND c.responsable=actor))
    ) THEN RAISE EXCEPTION 'Acceso denegado'; END IF;
    IF solicitud IS NULL OR jsonb_typeof(conceptos) IS DISTINCT FROM 'array' THEN
        RAISE EXCEPTION 'Solicitud inválida';
    END IF;
    IF jsonb_array_length(conceptos) NOT BETWEEN 1 AND 30 THEN
        RAISE EXCEPTION 'Se requieren de 1 a 30 conceptos';
    END IF;

    -- Una serie para el laboratorio. El bloqueo se libera al terminar la transacción.
    PERFORM 1 FROM series_factura WHERE serie='A' FOR UPDATE;
    SELECT * INTO anterior FROM facturas WHERE usuario_id=actor AND clave=solicitud;
    IF FOUND THEN
        IF anterior.cliente_id<>cliente OR anterior.conceptos_solicitados<>conceptos THEN
            RAISE EXCEPTION 'La clave ya corresponde a otra solicitud';
        END IF;
        resultado := anterior.folio;
        RETURN;
    END IF;

    -- Leer tarifas una sola vez para que detalle y totales compartan los mismos precios.
    SELECT jsonb_agg(jsonb_build_object('id',s.servicio_id,'nombre',s.nombre,
              'precio',s.precio,'cantidad', (x.item->>'cantidad')::integer) ORDER BY x.pos),
           sum(s.precio * (x.item->>'cantidad')::integer),sum((x.item->>'cantidad')::integer)
      INTO lineas, subtotal_calc, unidades
      FROM jsonb_array_elements(conceptos) WITH ORDINALITY AS x(item,pos)
      JOIN servicios s ON to_jsonb(s.servicio_id)=x.item->'servicio'
     WHERE jsonb_typeof(x.item->'cantidad')='number' AND (x.item->>'cantidad') ~ '^[1-9][0-9]{0,2}$';
    IF coalesce(jsonb_array_length(lineas),0)<>jsonb_array_length(conceptos) THEN
        RAISE EXCEPTION 'Servicio o cantidad inválidos';
    END IF;
    CALL aplicar_descuento(subtotal_calc,unidades,descuento_calc);
    CALL calcular_importes(subtotal_calc-descuento_calc,CURRENT_DATE,iva_calc,ret_calc,total_calc);
    UPDATE series_factura SET ultimo=ultimo+1 WHERE serie='A' RETURNING ultimo INTO STRICT resultado;
    INSERT INTO facturas(folio,usuario_id,cliente_id,clave,conceptos_solicitados,subtotal,descuento,iva,retencion,total)
    VALUES(resultado,actor,cliente,solicitud,conceptos,subtotal_calc,descuento_calc,iva_calc,ret_calc,total_calc);
    INSERT INTO detalle_factura(folio,renglon,servicio_id,descripcion,precio,cantidad)
    SELECT resultado,pos,(item->>'id')::integer,item->>'nombre',(item->>'precio')::numeric,(item->>'cantidad')::integer
      FROM jsonb_array_elements(lineas) WITH ORDINALITY AS x(item,pos);
END;
$$;
COMMIT;
