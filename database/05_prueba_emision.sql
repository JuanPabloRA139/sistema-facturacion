-- Ejecutar en una base de pruebas tras los archivos 01 a 04.
BEGIN;
DO $$
DECLARE
    cliente_prueba bigint;
    operador text := 'prueba-' || txid_current();
    conceptos jsonb;
    folio1 bigint;
    folio2 bigint;
    clave uuid := '454d4953-494f-4000-8000-000000000001';
BEGIN
    INSERT INTO usuarios_roles VALUES (operador,'operador');
    INSERT INTO clientes(responsable,nombre,rfc) VALUES(operador,'Cliente de prueba','XAXX010101000')
      RETURNING cliente_id INTO cliente_prueba;
    SELECT jsonb_build_array(jsonb_build_object('servicio',servicio_id,'cantidad',1))
      INTO STRICT conceptos FROM servicios WHERE codigo='S1';
    CALL emitir_factura(operador,cliente_prueba,clave,conceptos,folio1);
    CALL emitir_factura(operador,cliente_prueba,clave,conceptos,folio2);
    IF folio1 IS DISTINCT FROM folio2 OR NOT EXISTS (SELECT 1 FROM facturas
        WHERE folio=folio1 AND subtotal=105 AND iva=16.80 AND retencion=4.20 AND total=117.60) THEN
        RAISE EXCEPTION 'Falló el cálculo o se duplicó el folio';
    END IF;
    IF (SELECT count(*) FROM detalle_factura WHERE folio=folio1)<>1 THEN
        RAISE EXCEPTION 'Detalle duplicado';
    END IF;
    RAISE NOTICE 'Emisión correcta: total 117.60, mismo folio al reintentar.';
END;
$$;
ROLLBACK;
