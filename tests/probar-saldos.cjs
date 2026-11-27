const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {createRequire} = require('node:module');
const path = require('node:path');
const {PGlite} = createRequire(path.join(process.argv[2], 'package.json'))('@electric-sql/pglite');

async function verificar() {
  const db = new PGlite();
  try {
    const sql = nombre => readFileSync(path.join(__dirname, '..', 'database', nombre + '.sql'), 'utf8');
    for (const nombre of ['01_catalogo','02_datos_catalogo','03_facturacion','04_procedimientos',
                          '06_operaciones','08_auditoria']) await db.exec(sql(nombre));
    await db.exec(`
      INSERT INTO usuarios_roles VALUES ('alfa','operador'),('beta','operador'),('lector','auditor');
      INSERT INTO clientes(responsable,nombre,rfc) VALUES
        ('alfa','Ejemplo A','XAXX010101000'),('beta','Ejemplo B','XAXX010101000');
      DO $$ DECLARE i integer; resultado bigint;
      BEGIN
        FOR i IN 1..201 LOOP
          CALL emitir_factura('alfa',1,md5(i::text)::uuid,'[{"servicio":1,"cantidad":1}]',resultado);
        END LOOP;
        CALL emitir_factura('beta',2,md5('beta')::uuid,'[{"servicio":1,"cantidad":1}]',resultado);
      END; $$;
      UPDATE facturas SET vence=current_date-8 WHERE folio=201;
      CREATE ROLE facturacion_app LOGIN;
    `);
    await db.exec(sql('10_permisos_runtime'));
    await db.exec('SET ROLE facturacion_app');
    const saldos = async (usuario, pagina) => (await db.query(
      'CALL antiguedad_saldos($1,$2::jsonb)', [usuario, pagina ? JSON.stringify(pagina) : null])).rows[0].resultado;
    await db.query("CALL registrar_pago('alfa',1,'PARCIAL',50,NULL,NULL)");
    const ventana = await saldos('alfa', {paginado:true});
    const legado = await saldos('alfa', null);
    assert.equal(ventana.length, 201);
    assert.deepEqual(ventana.slice(0, 200), legado);
    assert.equal(ventana[0].folio, 201);
    assert.equal(ventana[0].dias_vencidos, 8);
    const ultimo = legado.at(-1);
    const paginaDos = {paginado:true, despues_de:{vence:ultimo.vence,folio:ultimo.folio}};
    const final = await saldos('alfa', paginaDos);
    assert.deepEqual(final, ventana.slice(200));
    const filas = [...legado, ...final];
    assert.equal(new Set(filas.map(f => f.folio)).size, 201);
    assert.equal(filas.reduce((s, f) => s + Math.round(Number(f.saldo)*100), 0), 201*11760-5000);
    assert.equal(filas.some(f => f.folio === 202), false);
    assert.deepEqual((await saldos('beta', paginaDos)).map(f => f.folio), [202]);
    assert.deepEqual((await saldos('lector', paginaDos)).map(f => f.folio), [200,202]);
    await db.query("CALL registrar_pago('alfa',1,'RESTO',67.6,NULL,NULL)");
    const exacta = await saldos('alfa', {paginado:true});
    assert.equal(exacta.length, 200);
    assert.equal(exacta.some(f => f.folio === 1), false);
    console.log('Cartera PostgreSQL: 201 saldos recuperados, cursor estable y alcance por operador verificados.');
  } finally {
    await db.close();
  }
}
verificar().catch(error => { console.error(error.message); process.exitCode = 1; });
