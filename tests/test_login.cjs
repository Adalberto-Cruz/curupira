// Login de exportação: só admin/admin passa.
const test=require('node:test'),assert=require('node:assert');
const L=require('../dist/assets/login.js');
test('aceita admin/admin',()=>{assert.ok(L.confere('admin','admin'));assert.ok(L.confere(' Admin ','admin'));});
test('recusa errado ou vazio',()=>{for(const [u,s] of [['admin','Admin'],['admin',''],['','admin'],['root','admin'],[undefined,undefined]])assert.ok(!L.confere(u,s));});
test('protege todos os botões de exportar',()=>{for(const id of ['export-data','export-map','download-geometry','report-download','report-print','env-export'])assert.ok(L.BOTOES.includes(id));});
