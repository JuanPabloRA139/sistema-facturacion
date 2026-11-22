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

COMMIT;
