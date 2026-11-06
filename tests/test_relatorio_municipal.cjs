// Gera o relatório municipal com dados reais e um DOM falso, para pegar erro de execução.
const test=require('node:test'),assert=require('node:assert'),fs=require('fs'),vm=require('vm');
const src=fs.readFileSync('dist/assets/app.js','utf8');
const ini=src.indexOf('// Relatório do município');
const deter=src.slice(src.indexOf('const deterNames='),src.indexOf('async function openReport'));
test('relatório de Barcelos sai com todas as seções',async()=>{
 const el={innerHTML:'',showModal(){},close(){}},btns={};
 const ctx=vm.createContext({
  state:{status:''},statusInfo:{AT:{name:'Ativo',plural:'Ativos'},PE:{name:'Pendente',plural:'Pendentes'}},
  muni:c=>({code:c,name:'Barcelos'}),recordsFor:async c=>JSON.parse(fs.readFileSync(`dist/data/cadastros/${c}.json`,'utf8')),
  fetchJSON:async u=>JSON.parse(fs.readFileSync('dist/'+u.split('?')[0],'utf8')),
  esc:s=>String(s),fmt:(v,d=0)=>Number(v).toFixed(d),date:v=>String(v).slice(0,10),brand:()=>'',icon:()=>'',
  catalog:{source_sha256:'x'},document:{title:''},
  $:q=>q==='#report-dialog'?el:(btns[q]=btns[q]||{}),Promise,JSON,Object,Number,Set,String,Date});
 vm.runInContext(deter+src.slice(ini),ctx);
 await ctx.openMunicipalityReport('1300409');
 for(const h of ['01. Filtros','02. Cadastros','03. Alertas','04. Contexto','05. Imóveis','06. Água','07. Limitações'])assert.match(el.innerHTML,new RegExp(h));
 assert.doesNotMatch(el.innerHTML,/undefined|NaN/);
 assert.match(el.innerHTML,/Somente alertas/);
 // troca para só alertas
 let novo='';el.querySelector=()=>({set outerHTML(v){novo=v;}});btns['#muni-modo'].onclick();
 assert.match(novo,/RELATÓRIO DE ALERTAS/);assert.match(novo,/Lista de alertas/);assert.doesNotMatch(novo,/undefined|NaN/);
});
