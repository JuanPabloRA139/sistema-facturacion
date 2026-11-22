const { test } = require('node:test');
const assert = require('node:assert/strict');
const { formatoRfcValido } = require('../frontend/rfc.js');
for (const [valor, esperado] of [
  ['ZETA000229AB1', true], [' zzz991231aa0 ', true],
  ['ZETA010229AB1', false], ['ZETA991301AB1', false],
  ['ZETA991200AB1', false], ['ZETA000229ABZ', false],
  ['ZZ000229AB1', false], ['', false], [null, false]
]) {
  test('Formato y fecha: ' + String(valor), () => assert.equal(formatoRfcValido(valor), esperado));
}
