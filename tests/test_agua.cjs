// Testes do indicador de pressão sobre a água (front e dados).
const test=require('node:test'),assert=require('node:assert');
const fs=require('fs'),path=require('path');
const agua=require('../dist/assets/agua.js');
const doc=JSON.parse(fs.readFileSync(path.join(__dirname,'../dist/data/agua/indicador.json'),'utf8'));
test('sem município pede seleção',()=>{assert.match(agua.html('',doc),/Selecione um município/);});
test('fora do AM não mostra número',()=>{const h=agua.html('5103403',doc);assert.match(h,/somente para municípios do Amazonas/);assert.doesNotMatch(h,/\/100/);});
test('Lábrea mostra score e aviso de estimativa',()=>{const h=agua.html('1302405',doc);assert.match(h,/\/100/);assert.match(h,/Estimativa por regras/);assert.match(h,/turbidez por satélite em desenvolvimento/);});
test('62 municípios, scores entre 0 e 100',()=>{const m=Object.values(doc.municipios);assert.equal(m.length,62);for(const v of m){assert.ok(v.score>=0&&v.score<=100);assert.ok(['baixa','média','alta'].includes(v.classe));}});
test('pesos somam 1',()=>{const s=Object.values(doc.metodo.pesos).reduce((a,b)=>a+b,0);assert.ok(Math.abs(s-1)<1e-9);});
test('escapa HTML do aviso',()=>{const h=agua.html('1',{aviso:'<x>',municipios:{'1':{score:1,classe:'baixa',contagens:{mineracao_deter:0,anm_extracao:0,desmatamento_recente:0}}}});assert.doesNotMatch(h,/<x>/);});
