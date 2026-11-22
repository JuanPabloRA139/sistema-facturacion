BEGIN;
INSERT INTO servicios (codigo, nombre, precio)
SELECT 'S' || n, 'Servicio de prueba ' || n, 100 + n * 5
FROM generate_series(1, 100) AS serie(n)
ON CONFLICT (codigo) DO NOTHING;
INSERT INTO caracteristicas (codigo, nombre)
SELECT 'C' || n, 'Característica de prueba ' || n
FROM generate_series(1, 50) AS serie(n)
ON CONFLICT (codigo) DO NOTHING;
COMMIT;
