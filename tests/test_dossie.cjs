// Testa a seção 03 do dossiê do CAR com dados reais e com falha de carga.
const test=require('node:test'),assert=require('node:assert'),fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('dist/assets/app.js','utf8');
const ini=src.indexOf('const deterNames='),fim=src.length;
const ctx=vm.createContext({esc:s=>String(s).replace(/[&<>"']/g,''),fmt:(v,d)=>Number(v).toFixed(d)});
vm.runInContext(src.slice(ini,fim).replace('async function openReport','async function _o'),ctx);
const att=JSON.parse(fs.readFileSync('dist/data/atencao/municipios/1301704.json','utf8'));
const code='AM-1301704-011103189A83450BBDA7F02282FCEFE9';
test('CAR com embargo mostra nota e embargo',()=>{
 const car=att.by_car[code];assert.ok(car,'CAR do print existe no índice');
 const h=ctx.reportEnvironment({car,disclaimer:att.disclaimer,water:{score:50,classe:'média'}});
 assert.match(h,/Índice de atenção/);assert.match(h,/Áreas embargadas/);assert.match(h,/50 \/ 100/);assert.doesNotMatch(h,/undefined|NaN/);
});
test('sem dados carregados não inventa números',()=>{const h=ctx.reportEnvironment({});assert.match(h,/Não foi possível carregar/);assert.doesNotMatch(h,/\/ 100/);});
test('água indisponível aparece como indisponível',()=>{const h=ctx.reportEnvironment({car:{nota:0,contagens:{}}});assert.match(h,/Indisponível/);assert.doesNotMatch(h,/undefined|NaN/);});
