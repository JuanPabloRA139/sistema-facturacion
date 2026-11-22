// PGlite se instala en la caché del usuario. Las tablas de esta prueba viven en memoria.
const { readFileSync } = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const dependencias = createRequire(path.join(process.argv[2], 'package.json'));
const { PGlite } = dependencias('@electric-sql/pglite');
const scripts = [
  '01_catalogo.sql', '02_datos_catalogo.sql', '03_facturacion.sql',
  '04_procedimientos.sql', '05_prueba_emision.sql', '06_operaciones.sql',
  '07_prueba_operaciones.sql'
];

async function probar() {
  const db = new PGlite();
  try {
    for (const archivo of scripts) {
      console.log('Ejecutando', archivo);
      await db.exec(readFileSync(path.join(__dirname, '..', 'database', archivo), 'utf8'));
    }
    console.log('PRUEBA SUPERADA: factura $117.60, pago $50.00 y saldo $67.60 tras repetir el pago.');
  } finally {
    await db.close();
  }
}
probar().catch(error => { console.error(error.message); process.exitCode = 1; });
