// Validación preliminar de estructura y fecha. El sufijo se revisa por forma.
function formatoRfcValido(valor) {
  if (typeof valor !== 'string') return false;
  const partes = /^([A-ZÑ&]{3,4})(\d{2})(\d{2})(\d{2})([A-Z0-9]{2}[0-9A])$/u.exec(valor.trim().toUpperCase());
  if (!partes) return false;
  const anio = 2000 + Number(partes[2]);
  const mes = Number(partes[3]);
  const dia = Number(partes[4]);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  return fecha.getUTCMonth() === mes - 1 && fecha.getUTCDate() === dia;
}
if (typeof module !== 'undefined') module.exports = { formatoRfcValido };
