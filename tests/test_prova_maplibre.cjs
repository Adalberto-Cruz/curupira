'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {cameraZoom, featureTarget, carLayers} = require('../dist/assets/prova-maplibre-model.js');
const palette = require('../dist/data/ambiental/paleta.json');
test('câmera mantém a escala de pixels Leaflet de 256 para MapLibre de 512', () => {
  for (const zoom of [6, 12, 19]) assert.equal(512 * 2 ** cameraZoom(zoom), 256 * 2 ** zoom);
});
test('código string identifica o mesmo CAR em fragmentos de tiles', () => {
  const code = 'AM-1302603-D3F7431D65D14199BDE0CE9CE881A896';
  assert.deepEqual(featureTarget(code), {source: 'car', sourceLayer: 'car', id: code});
});
test('quatro situações preservam cores e tracejados; seleção independe da situação', () => {
  const layers = carLayers(palette);
  for (const [status, style] of Object.entries(palette.cars)) {
    const line = layers.find(l => l.id === 'car-' + status);
    assert.equal(line.paint['line-color'], style.color);
    assert.deepEqual(line.filter, ['==', ['get', 'status'], status]);
    assert.deepEqual(line.paint['line-dasharray'], style.dashArray ? style.dashArray.split(' ').map(Number) : undefined);
  }
  const selected = layers.at(-1);
  assert.equal(selected.filter, undefined);
  assert.equal(selected.paint['line-color'], '#ffffff');
  assert.deepEqual(selected.paint['line-width'], ['case', ['boolean', ['feature-state', 'selected'], false], 3, 0]);
});
