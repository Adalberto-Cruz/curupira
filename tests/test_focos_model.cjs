const test=require('node:test'),assert=require('node:assert/strict');
const M=require('../dist/assets/focos-model.js');
test('classes fixas preservam limites e sem contagem',()=>{
 assert.deepEqual([null,0,1,10,11,50,51,200,201,1000,1001,5000,5001].map(n=>M.classify(n,[0,10,50,200,1000,5000])),[-1,0,1,1,2,2,3,3,4,4,5,5,6]);
});
test('12 meses fechados atravessam anos sem incluir novembro provisório',()=>{
 const p=M.periods({default_period:{start:'2025-11',end:'2026-10'}},'latest');
 assert.equal(p.length,12);assert.equal(p[0],'2025-11');assert.equal(p.at(-1),'2026-10');
});
test('meses indisponíveis nunca viram zero, áreas operacionais não recebem contagem',()=>{
 const index=[{kind:'municipio'},{kind:'operacional'}],files={'2026':{months:['complete','unavailable'],monthly:[[8,0],null]}};
 assert.deepEqual(M.aggregate(index,files,['2026-01'],{'2026-01':{}}),[8,null]);
 assert.throws(()=>M.aggregate(index,files,['2026-02'],{'2026-02':{}}),/indisponível/);
 assert.throws(()=>M.aggregate(index,files,[],{}),/sem dados/);
});
test('ano parcial só usa meses disponíveis e permite mês provisório',()=>{
 const manifest={coverage:{'2026-10':{status:'complete'},'2026-11':{status:'provisional'}}};
 assert.deepEqual(M.periods(manifest,'year','2026'),['2026-10','2026-11']);
 assert.deepEqual(M.periods(manifest,'month','2026',11),['2026-11']);
});
