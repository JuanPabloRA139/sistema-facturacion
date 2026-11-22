// Dos motores independientes en memoria para verificar el límite entre instancias.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const { PGlite } = createRequire(path.join(process.argv[2], "package.json"))("@electric-sql/pglite");

async function verificar() {
  const negocio = new PGlite();
  const identidad = new PGlite();
  const script = nombre => fs.readFileSync(path.join(__dirname, "..", "database", nombre + ".sql"), "utf8");
  try {
    for (const nombre of ["01_catalogo", "02_datos_catalogo", "03_facturacion", "04_procedimientos", "06_operaciones", "08_auditoria"]) {
      await negocio.exec(script(nombre));
    }
    await identidad.exec(script("09_identidades"));
    await identidad.exec(script("09_identidades"));
    await negocio.query("INSERT INTO usuarios_roles VALUES ($1,$2)", ["demo", "operador"]);
    const { rows } = await negocio.query("SELECT usuario_id, rol FROM usuarios_roles");
    for (const usuario of rows) {
      await identidad.query("INSERT INTO usuarios_roles VALUES ($1,$2)", [usuario.usuario_id, usuario.rol]);
    }
    await identidad.exec("CREATE ROLE identidad_lectura; GRANT USAGE ON SCHEMA public TO identidad_lectura; GRANT SELECT ON usuarios_roles TO identidad_lectura; SET ROLE identidad_lectura");
    assert.equal((await identidad.query("SELECT rol FROM usuarios_roles WHERE usuario_id=$1", ["demo"])).rows[0].rol, "operador");
    await assert.rejects(identidad.query("UPDATE usuarios_roles SET rol='administrador'"), {code: "42501"});
    assert.equal((await identidad.query("SELECT to_regclass('public.facturas') AS tabla")).rows[0].tabla, null);
    console.log("Directorio independiente, lectura de roles y rechazo de escritura comprobados.");
  } finally {
    await negocio.close();
    await identidad.close();
  }
}
verificar().catch(error => { console.error(error.message); process.exitCode = 1; });
