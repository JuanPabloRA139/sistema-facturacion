PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS usuarios_roles(usuario TEXT PRIMARY KEY,rol TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clientes(id INTEGER PRIMARY KEY,nombre TEXT NOT NULL,rfc TEXT NOT NULL,usuario TEXT NOT NULL REFERENCES usuarios_roles, UNIQUE(usuario,rfc));
CREATE TABLE IF NOT EXISTS servicios(id INTEGER PRIMARY KEY,nombre TEXT NOT NULL,precio INTEGER NOT NULL CHECK(precio>0));
CREATE TABLE IF NOT EXISTS caracteristicas(id INTEGER PRIMARY KEY,nombre TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS caracteristicas_servicio(servicio INTEGER REFERENCES servicios,caracteristica INTEGER REFERENCES caracteristicas,PRIMARY KEY(servicio,caracteristica));
CREATE TABLE IF NOT EXISTS impuestos_historico(desde TEXT PRIMARY KEY,iva INTEGER NOT NULL,retencion INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS facturas(id INTEGER PRIMARY KEY AUTOINCREMENT,cliente INTEGER NOT NULL REFERENCES clientes,usuario TEXT NOT NULL REFERENCES usuarios_roles,clave TEXT NOT NULL,solicitud TEXT NOT NULL,fecha TEXT NOT NULL,vence TEXT NOT NULL,subtotal INTEGER NOT NULL,descuento INTEGER NOT NULL,iva INTEGER NOT NULL,retencion INTEGER NOT NULL,total INTEGER NOT NULL,estado TEXT NOT NULL DEFAULT 'emitida', UNIQUE(usuario,clave));
CREATE TABLE IF NOT EXISTS detalle_factura(factura INTEGER REFERENCES facturas,servicio INTEGER REFERENCES servicios,nombre TEXT NOT NULL,precio INTEGER NOT NULL,cantidad INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS pagos(id INTEGER PRIMARY KEY,factura INTEGER NOT NULL REFERENCES facturas,referencia TEXT NOT NULL,importe INTEGER NOT NULL CHECK(importe>0),UNIQUE(factura,referencia));
CREATE TABLE IF NOT EXISTS auditoria(id INTEGER PRIMARY KEY,fecha TEXT DEFAULT CURRENT_TIMESTAMP,usuario TEXT NOT NULL,accion TEXT NOT NULL,entidad TEXT NOT NULL,detalle TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS motivos_cancelacion(
    evento INTEGER PRIMARY KEY REFERENCES auditoria(id),
    motivo TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cierres(periodo TEXT PRIMARY KEY,fecha TEXT DEFAULT CURRENT_TIMESTAMP,neto INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS movimientos(id INTEGER PRIMARY KEY,fecha TEXT NOT NULL,factura INTEGER REFERENCES facturas,concepto TEXT NOT NULL,importe INTEGER NOT NULL,UNIQUE(factura,concepto));
CREATE INDEX IF NOT EXISTS idx_facturas_usuario ON facturas(usuario,id);
CREATE INDEX IF NOT EXISTS idx_detalle ON detalle_factura(factura);
CREATE INDEX IF NOT EXISTS idx_mov_fecha ON movimientos(fecha);
CREATE INDEX IF NOT EXISTS idx_saldos_vencimiento ON facturas(vence,id) WHERE estado IN ('emitida','parcial');
