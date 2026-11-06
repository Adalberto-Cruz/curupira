const test=require('node:test'),assert=require('node:assert/strict');
const A=require('../dist/assets/atencao.js');
const code='AM-1302603-'+'A'.repeat(32);
function row(nota=10){return {nota,travas:[],contribuicoes:{prodes:nota,deter:0,anm:0,focos:0,trava:0},area_car_ha:100,prodes_no_car_ha:25,fracao_prodes:.25,situacao:'AT',classes_deter:{}};}
function data(){return {version:'1.0.0',municipio:'1302603',disclaimer:A.DISCLAIMER,by_car:{[code]:row()},top20:[code]};}
test('base verifica índice, soma, ranking, escopo e aviso obrigatório',()=>{
 assert.equal(A.validateData(data(),'1302603').by_car[code].nota,10);
 const d=data();d.by_car[code].contribuicoes.deter=1;assert.throws(()=>A.validateData(d,'1302603'));
 assert.throws(()=>A.validateData(data(),'5103403'));
 const e=data();e.by_car[code].travas=['ti'];assert.throws(()=>A.validateData(e,'1302603'));
 const f=data();f.by_car[code].situacao='CA';assert.throws(()=>A.validateData(f,'1302603'));
 const g=data();g.disclaimer='';assert.throws(()=>A.validateData(g,'1302603'));
});
test('store não carrega automaticamente, reutiliza lote e permite tentativa após falha',async()=>{
 let calls=0,fail=true;const store=A.createStore(async()=>{calls++;return {ok:!fail,json:async()=>data()};});
 assert.equal(calls,0);await assert.rejects(store.load('1302603'));fail=false;
 const [a,b]=await Promise.all([store.load('1302603'),store.load('1302603')]);assert.equal(a,b);assert.equal(calls,2);
 await assert.rejects(store.load('5103403'));assert.equal(calls,2);
});
test('detalhe expõe contribuição, trava única e texto obrigatório com escape',()=>{
 const r=row();r.nota=100;r.travas=['ti','embargos'];r.contribuicoes.trava=90;
 const html=A.detailHTML(r);assert(html.includes('100'));assert(html.includes('Complemento da trava crítica'));assert(html.includes(A.DISCLAIMER));assert(html.includes('90 pontos'));
 r.classes_deter={'<script>alert(1)</script>':1};assert(!A.detailHTML(r).includes('<script>'));
});
test('resposta antiga não substitui detalhe de outro CAR',async()=>{
 let release;const source={load:()=>new Promise(r=>{release=r;})};const target={innerHTML:'',isConnected:true};let current=true;
 const pending=A.renderDetail(target,code,'1302603',()=>current,source);current=false;release(data());await pending;
 assert(!target.innerHTML.includes('attention-score'));
});
test('falha exibe indisponível e permite repetir sem presumir nota zero',async()=>{
 const button={};const target={innerHTML:'',isConnected:true,querySelector:()=>button};
 await A.renderDetail(target,code,'1302603',()=>true,{load:async()=>{throw Error('offline');}});
 assert(target.innerHTML.includes('não equivale a nota zero'));assert.equal(typeof button.onclick,'function');
});
