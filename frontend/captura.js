document.querySelector('#captura').addEventListener('submit', (evento) => {
  evento.preventDefault();
  const valor = document.querySelector('#rfc').value;
  document.querySelector('#resultado').textContent = formatoRfcValido(valor)
    ? 'Formato compatible. Inscripción pendiente de verificar.'
    : 'Revisa las letras iniciales, la fecha y los tres caracteres finales.';
});
