const campoRfc = document.querySelector('#rfc');
const resultado = document.querySelector('#resultado');

campoRfc.addEventListener('input', () => {
  resultado.textContent = '';
});

document.querySelector('#captura').addEventListener('submit', (evento) => {
  evento.preventDefault();
  resultado.textContent = formatoRfcValido(campoRfc.value)
    ? 'Formato compatible. Inscripción pendiente de verificar.'
    : 'Revisa las letras iniciales, la fecha y los tres caracteres finales.';
});
