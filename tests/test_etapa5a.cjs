const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const M=require('../dist/assets/map-state.js');
const root=path.resolve(__dirname,'..'),read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const catalog=read('dist/data/catalogo.json'),palette=read('dist/data/ambiental/paleta.json'),exceptions=read('dist/data/indice_car.json');
const entries=read('dist/data/busca-municipios.json').municipalities.map(([code,name,uf,bounds])=>({code,name,uf,bounds}));
const context={coverage:M.coverage(catalog),municipalities:new Set(catalog.municipalities.map(m=>m.code)),categories:new Set(Object.keys(palette.layers.deter.style.categories)),carMunicipality:car=>exceptions[car]||car.split('-')[1]};
test('busca local ignora acento, caixa e aceita trecho, UF e geocódigo',()=>{
 for(const query of ['novo airao','NOVO AIRÃO','vo air','Novo Airão AM','1303205'])assert.ok(M.search(entries,query,12,context.coverage).some(m=>m.name==='Novo Airão'&&m.uf==='AM'));
 assert.ok(M.search(entries,'São Paulo').some(m=>m.uf==='SP'));
 assert.equal(M.search(entries,'zzzzinexistente').length,0);
 assert.equal(M.search(entries,'').length,0);
});
test('estado completo compartilha todos os filtros sem perdas',()=>{
 const car=read('dist/data/cadastros/1302603.json')[0].code;
 const next={...M.defaults(),municipio:'1302603',car,camadas:['car','ti','anm','deter'],inicio:'2026-01-01',fim:'2026-11-04',classe:'MINERACAO',opacidade:35,base:'terrain',colorir:true};
 const restored=M.decode(M.serialize(next),context);
 assert.deepEqual(restored.state,next);assert.deepEqual(restored.warnings,[]);
 assert.equal(M.serialize(M.defaults()),'');
 assert.deepEqual(M.decode('',context),{state:M.defaults(),warnings:[]});
});
test('link parcial recebe padrões e aviso; CAR infere município existente',()=>{
 const car=read('dist/data/cadastros/1302603.json')[0].code;
 const partial=M.decode('?car='+car.toLowerCase(),context);
 assert.equal(partial.state.car,car);assert.equal(partial.state.municipio,'1302603');assert.ok(partial.warnings.length);
});
test('parâmetros inválidos, repetidos, incompatíveis e desconhecidos não quebram estado',()=>{
 const bad=M.decode('?municipio=3550308&car=<script>&camadas=ti,BOGUS&inicio=2026-02-30&fim=2099-01-01&classe=INVENTADA&opacidade=NaN&base=javascript:1&colorir=sim&outro=1',context);
 assert.deepEqual(bad.state,M.defaults());assert.ok(bad.warnings.length>=8);
 assert.equal(M.serialize(bad.state),'');
 const duplicate=M.decode('?municipio=1302603&municipio=1303205',context);assert.equal(duplicate.state.municipio,'');assert.ok(duplicate.warnings.some(w=>w.includes('repetido')));
 const car=read('dist/data/cadastros/1302603.json')[0].code;
 const incompatible=M.decode('?municipio=1303205&car='+car,context);assert.equal(incompatible.state.municipio,'1303205');assert.equal(incompatible.state.car,'');
});
test('datas, opacidade e camadas vazias são validadas sem confundir ausência com desligamento',()=>{
 assert.equal(M.validDate('2024-02-29'),true);assert.equal(M.validDate('2025-02-29'),false);
 assert.equal(M.validDate('2026-11-06'),false);
 const reverse=M.decode('?inicio=2026-11-04&fim=2026-01-01&opacidade=101',context);assert.equal(reverse.state.inicio,'');assert.equal(reverse.state.fim,'');assert.equal(reverse.state.opacidade,65);
 const none=M.decode(M.serialize({...M.defaults(),camadas:[]}),context);assert.deepEqual(none.state.camadas,[]);assert.equal(none.warnings.length,0);
});
test('ponto em polígono inclui divisa e exclui buraco e exterior; aceita multipolígono',()=>{
 const square=[[0,0],[4,0],[4,4],[0,4],[0,0]],hole=[[1,1],[3,1],[3,3],[1,3],[1,1]];
 const poly={type:'Polygon',coordinates:[square,hole]};
 assert.equal(M.covers(poly,.5,.5),true);assert.equal(M.covers(poly,2,2),false);assert.equal(M.covers(poly,1,2),true);assert.equal(M.covers(poly,0,0),true);assert.equal(M.covers(poly,9,9),false);
 assert.equal(M.covers({type:'MultiPolygon',coordinates:[[square]]},2,2),true);
});
test('classes DETER vêm do catálogo antes do recorte e cliques em CAR não propagam ao fundo',()=>{
 const environmental=fs.readFileSync(path.join(root,'dist/assets/ambiental.js'),'utf8');
 assert.match(environmental,/Object\.entries\(categories\)/);
 assert.doesNotMatch(environmental,/category\.innerHTML/);
 const app=fs.readFileSync(path.join(root,'dist/assets/app.js'),'utf8');
 assert.match(app,/carLayer=L\.geoJSON\(geo,\{bubblingMouseEvents:false/);
 assert.match(app,/countyLayer=L\.geoJSON\(municipalitiesGeo,\{bubblingMouseEvents:false/);
});
test('cobertura configurada suporta outras UFs em validação, mensagem e prioridade',()=>{
 const configured=M.coverage({car_ufs:['PA','SP']});
 assert.deepEqual(configured.ufs,['PA','SP']);
 assert.equal(M.coverageMessage(configured),'CAR disponível somente nas UFs: PA e SP.');
 const code='PA-1506807-'+'A'.repeat(32);
 assert.equal(M.isCarCode(code,configured),true);
 assert.equal(M.isCarCode('SP-3550308-'+'B'.repeat(32),configured),true);
 assert.equal(M.isCarCode('AM-1302603-'+'C'.repeat(32),configured),false);
 const restored=M.decode('?car='+code,{...context,coverage:configured,municipalities:new Set(['1506807'])});
 assert.equal(restored.state.car,code);assert.equal(restored.state.municipio,'1506807');
 const duplicates=[{code:'1',name:'Igual',uf:'AM'},{code:'2',name:'Igual',uf:'PA'}];
 assert.equal(M.search(duplicates,'Igual',12,configured)[0].uf,'PA');
});
test('cobertura ausente, vazia, duplicada ou malformada gera erro claro',()=>{
 for(const value of [{},{car_ufs:[]},{car_ufs:['AM','AM']},{car_ufs:['amazonas']},{car_ufs:'AM'}])assert.throws(()=>M.coverage(value),/Cobertura CAR.*catalogo\.json/);
});
