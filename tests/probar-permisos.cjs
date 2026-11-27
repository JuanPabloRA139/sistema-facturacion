// PostgreSQL embebido. Verifica actualización del esquema y derechos efectivos.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { PGlite } = createRequire(path.join(process.argv[2], 'package.json'))('@electric-sql/pglite');
const sql = nombre => fs.readFileSync(path.join(__dirname, '..', 'database', nombre + '.sql'), 'utf8').trim();
const esquema = ['01_catalogo','02_datos_catalogo','03_facturacion','04_procedimientos','06_operaciones','08_auditoria'];

async function verificar() {
  const db = new PGlite();
  try {
    await db.exec(`CREATE ROLE facturacion_deploy LOGIN CREATEROLE;
      ALTER SCHEMA public OWNER TO facturacion_deploy;
      SET ROLE facturacion_deploy;
      CREATE ROLE facturacion_app LOGIN;`);
    for (const nombre of esquema) await db.exec(sql(nombre));
    // Permisos existentes que afectan los controles que se ensayan abajo.
    await db.exec(`GRANT SELECT,INSERT ON facturas,pagos,clientes,eventos_pendientes TO facturacion_app;
      GRANT UPDATE(estado) ON facturas TO facturacion_app;
      GRANT UPDATE(precio) ON servicios TO facturacion_app;
      GRANT UPDATE(ultimo) ON series_factura TO facturacion_app;
      GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO facturacion_app;
      GRANT EXECUTE ON ALL ROUTINES IN SCHEMA public TO facturacion_app;
      INSERT INTO usuarios_roles VALUES ('operador','operador'),('admin','administrador');`);
    async function comprobarRechazoDePropietario() {
      await db.exec('BEGIN');
      await assert.rejects(db.exec(sql('10_permisos_runtime')), /contrato de seguridad/);
      await db.exec('ROLLBACK');
      const previa = await db.query("SELECT has_table_privilege('facturacion_app','pagos','INSERT') AS intacto");
      assert.equal(previa.rows[0].intacto,true);
    }
    await db.exec("CREATE ROLE facturacion_operaciones LOGIN; COMMENT ON ROLE facturacion_operaciones IS 'facturacion-servicios:propietario-operaciones:v1'");
    await comprobarRechazoDePropietario();
    await db.exec("ALTER ROLE facturacion_operaciones NOLOGIN; CREATE ROLE permisos_ajenos; GRANT permisos_ajenos TO facturacion_operaciones");
    await comprobarRechazoDePropietario();
    await db.exec('REVOKE permisos_ajenos FROM facturacion_operaciones; COMMENT ON ROLE facturacion_operaciones IS NULL');
    await comprobarRechazoDePropietario();
    await db.exec('DROP ROLE facturacion_operaciones; DROP ROLE permisos_ajenos');
    // Dos despliegues, con el mismo propietario sin privilegio de superusuario.
    for (let intento = 0; intento < 2; intento++) {
      await db.exec('BEGIN');
      for (const nombre of esquema) {
        await db.exec(sql(nombre).replace(/^BEGIN;/, '').replace(/COMMIT;$/, ''));
      }
      await db.exec(sql('10_permisos_runtime'));
      await db.exec('COMMIT');
    }
    await db.exec('RESET ROLE; SET ROLE facturacion_app');
    const una = async (texto, parametros = []) => (await db.query(texto, parametros)).rows[0];
    assert.equal((await una("SELECT rolsuper OR rolcreaterole OR rolcreatedb OR rolcanlogin AS inseguro FROM pg_roles WHERE rolname='facturacion_operaciones'")).inseguro, false);
    assert.equal((await una("SELECT pg_has_role(current_user,'facturacion_operaciones','MEMBER') AS acceso")).acceso,false);
    assert.equal((await una("SELECT has_schema_privilege('facturacion_operaciones','public','CREATE') AS ok")).ok,false);
    for (const [tabla,permiso] of [['facturas','INSERT'], ['pagos','INSERT'], ['eventos_pendientes','INSERT']]) {
      assert.equal((await una("SELECT has_table_privilege(current_user,$1,$2) AS ok",[tabla,permiso])).ok,false);
    }
    for (const [tabla,columna,permiso] of [['facturas','estado','UPDATE'],['servicios','precio','UPDATE'],['clientes','rfc','SELECT']]) {
      assert.equal((await una("SELECT has_column_privilege(current_user,$1,$2,$3) AS ok",[tabla,columna,permiso])).ok,false);
    }
    await db.exec('BEGIN');
    await db.query("SELECT set_config('facturacion.actor','operador',true)");
    const {cliente_id} = await una("INSERT INTO clientes(responsable,nombre,rfc) VALUES ('operador','Cliente','XAXX010101000') RETURNING cliente_id");
    const {servicio_id} = await una("SELECT servicio_id FROM servicios WHERE codigo='S1'");
    const lineas = JSON.stringify([{servicio:servicio_id,cantidad:1}]);
    const emitir = clave => una("CALL emitir_factura('operador',$1,$2::uuid,$3::jsonb,NULL)",[cliente_id,clave,lineas]);
    const {resultado:folio} = await emitir('10000000-0000-4000-8000-000000000001');
    const fila = await una("SELECT folio,fecha,total,estado FROM facturas WHERE usuario_id='operador' ORDER BY folio DESC LIMIT 100");
    const cliente = await una("SELECT cliente_id,nombre FROM clientes WHERE responsable='operador' ORDER BY cliente_id DESC LIMIT 500");
    assert.equal(fila.folio,folio);
    assert.equal(cliente.cliente_id,cliente_id);
    const pago = () => una("CALL registrar_pago('operador',$1,'pago-A',50,NULL,NULL)",[folio]);
    assert.equal((await pago()).repetido,false);
    assert.equal((await pago()).repetido,true);
    const recibo = await una("CALL generar_comprobante('operador',$1,NULL)",[folio]);
    assert.equal(Number(recibo.resultado.saldo),67.60);
    await db.query("CALL antiguedad_saldos('operador',NULL)");
    const {resultado:otro} = await emitir('10000000-0000-4000-8000-000000000002');
    await db.query("SELECT set_config('facturacion.actor','admin',true)");
    await db.query("CALL cancelar_factura('admin',$1,'Corrección')",[otro]);
    await db.query("CALL cambiar_tarifa('admin',$1,220)",[servicio_id]);
    await db.query("CALL asignar_caracteristicas('admin',$1::integer[],ARRAY[1])",[[servicio_id]]);
    await db.query("CALL cerrar_periodo('admin',CURRENT_DATE-1,false,NULL)");
    const eventos = await db.query("SELECT evento_id FROM eventos_pendientes WHERE NOT enviado FOR UPDATE SKIP LOCKED");
    assert.equal(eventos.rows.length,5);
    await db.query("UPDATE eventos_pendientes SET enviado=true WHERE evento_id=$1",[eventos.rows[0].evento_id]);
    await db.exec('COMMIT');
    console.log('Permisos migrados. Las ocho operaciones autorizadas y la cola de auditoría funcionan con el rol real de aplicación.');
  } finally {
    await db.close();
  }
}
verificar().catch(error => { console.error(error.message); process.exitCode = 1; });
