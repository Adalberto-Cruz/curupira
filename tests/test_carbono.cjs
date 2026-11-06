// Carbono estimado por regra no painel do imóvel.
const test=require('node:test'),assert=require('node:assert');
const A=require('../dist/assets/atencao.js');
test('imóvel com 27% desmatado',()=>{const c=A.carbono({area_car_ha:200,prodes_no_car_ha:54});assert.equal(Math.round(c.pct),73);assert.equal(c.estoque,146*A.C_POR_HA);assert.equal(c.perdido,54*A.C_POR_HA);});
test('área zero não dá NaN',()=>{const c=A.carbono({area_car_ha:0});assert.ok(Object.values(c).every(Number.isFinite));});
test('desmatamento maior que a área fica limitado',()=>{const c=A.carbono({area_car_ha:10,prodes_no_car_ha:12});assert.equal(c.pct,0);assert.equal(c.estoque,0);});
test('campos ausentes',()=>{const c=A.carbono({});assert.ok(Object.values(c).every(Number.isFinite));});
