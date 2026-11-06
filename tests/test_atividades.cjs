const test=require('node:test'),assert=require('node:assert/strict');
const A=require('../dist/assets/atividades.js'),M=require('../dist/assets/map-state.js');
const current=()=>({...M.defaults(),municipio:'1302603',car:'AM-1302603-'+'A'.repeat(32),inicio:'2025-01-01',fim:'2025-12-31',base:'terrain',opacidade:35});
test('atalhos ativam as camadas existentes, preservando CAR, datas e outras camadas',()=>{
 const expected={ti:['ti'],desmatamento:['prodes','deter'],fogo:['deter'],embargos:['embargos'],madeira:['deter'],mineracao:['deter','anm']};
 for(const [id,layers] of Object.entries(expected)){
  const before=current(),snapshot=JSON.stringify(before),next=A.plan(id,before);
  for(const layer of layers)assert(next.camadas.includes(layer));
  for(const layer of before.camadas)assert(next.camadas.includes(layer));
  for(const key of ['municipio','car','inicio','fim','base','opacidade'])assert.equal(next[key],before[key]);
  assert.equal(JSON.stringify(before),snapshot);
 }
 assert.equal(A.plan('fogo',current()).focos,true);
 assert.equal(A.plan('fogo',current()).classe,'CICATRIZ_DE_QUEIMADA');
 assert.equal(A.plan('mineracao',current()).classe,'MINERACAO');
});
test('grupos DETER incluem só as duas classes de desmatamento e todas as variantes de corte seletivo',()=>{
 for(const category of ['DESMATAMENTO_CR','DESMATAMENTO_VEG'])assert(A.matchesClass(category,'ATIVIDADE_DESMATAMENTO'));
 for(const category of ['CS_DESORDENADO','CS_GEOMETRICO','CORTE_SELETIVO'])assert(A.matchesClass(category,'ATIVIDADE_CORTE_SELETIVO'));
 assert(!A.matchesClass('MINERACAO','ATIVIDADE_CORTE_SELETIVO'));
 assert(!A.matchesClass('CICATRIZ_DE_QUEIMADA','ATIVIDADE_DESMATAMENTO'));
 assert(!A.matchesClass('DESMATAMENTO_CR','MINERACAO'));
 assert(A.matchesClass('MINERACAO','MINERACAO'));assert(A.matchesClass('DEGRADACAO',''));
});
test('sem município não altera filtros e não aciona opções em desenvolvimento',()=>{
 const empty=M.defaults(),snapshot=JSON.stringify(empty);
 for(const d of A.definitions.filter(d=>!d.disabled))assert.throws(()=>A.plan(d.id,empty),/^Error: Selecione um município$/);
 assert.equal(JSON.stringify(empty),snapshot);
 assert.throws(()=>A.plan('inexistente',current()),/Em desenvolvimento/);
 assert.equal(A.definitions.filter(d=>d.disabled).length,0);
 assert.throws(()=>A.plan('ti',{...current(),municipio:'3550308'}),/Amazonas/);
});
test('links compartilhados restauram grupos de classes e focos sem perder filtros',()=>{
 const context={municipalities:new Set(['1302603']),coverage:{ufs:['AM']},carMunicipality:()=> '1302603',categories:new Set([...Object.keys(A.groups),'CICATRIZ_DE_QUEIMADA','MINERACAO'])};
 for(const id of ['desmatamento','madeira','fogo','mineracao']){
  const state=A.plan(id,current());
  assert.deepEqual(M.decode(M.serialize(state),context).state,{...state,camadas:M.layerIds.filter(k=>state.camadas.includes(k))});
 }
});
test('TI e DETER ativos por padrão; link com escolha explícita continua respeitado',()=>{
 assert.deepEqual(M.defaults().camadas,['municipios','car','ti','deter']);
 const context={municipalities:new Set(),coverage:{ufs:['AM']},carMunicipality:()=>'',categories:new Set()};
 assert.deepEqual(M.decode('?camadas=municipios,car',context).state.camadas,['municipios','car']);
});
