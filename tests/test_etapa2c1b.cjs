const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),zlib=require('node:zlib'),crypto=require('node:crypto');
const M=require('../dist/assets/focos-model.js'),S=require('../dist/assets/map-state.js'),{createStore}=require('../dist/assets/focos-brasil.js');
const root=path.resolve(__dirname,'..');
function fixture(){
 const files={},requests=[],units=[{code:'1',name:'Um',uf:'XX',kind:'municipio'},{code:'2',name:'Dois',uf:'XX',kind:'municipio'},{code:'3',name:'Lago',uf:'XX',kind:'operacional'}];
 const product=(name,value)=>{const bytes=zlib.gzipSync(JSON.stringify(value));files[name]=bytes;return {path:name,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};};
 const coverage={};for(let i=1;i<=12;i++)coverage['2003-'+String(i).padStart(2,'0')]={status:'complete'};coverage['2026-01']={status:'complete'};
 const manifest={version:1,units:3,as_of:'2026-11-06',classes:[0,10,50,200,1000,5000],class_colors:['a','b','c','d','e','f','g'],coverage,
  index:product('index.gz',{units}),mesh:product('mesh.gz',{features:units.map((m,i)=>({id:m.code,properties:{i}}))}),years:{}};
 manifest.years['2003']=product('2003.gz',{year:2003,months:Array(12).fill('complete'),annual:[0,4,null],monthly:[Array(12).fill(0),[4,...Array(11).fill(0)],null]});
 manifest.years['2026']=product('2026.gz',{year:2026,months:['complete',...Array(11).fill('unavailable')],annual:[2,0,null],monthly:[[2,...Array(11).fill(0)],Array(12).fill(0),null]});
 files['manifesto.json']=Buffer.from(JSON.stringify(manifest));
 return {files,requests,manifest,fetcher:async url=>{requests.push(url);const bytes=files[url.split('/').at(-1)];return new Response(bytes||'ausente',{status:bytes?200:404});}};
}
test('store não faz carga inicial, valida gzip/hash e reutiliza os mesmos arquivos',async()=>{
 const f=fixture(),store=createStore({model:M,fetcher:f.fetcher});assert.equal(f.requests.length,0);
 const annual=await store.annual('2003');assert.deepEqual(annual.values,[0,4,null]);assert.equal(f.requests.length,4);
 await store.annual('2003');assert.equal(f.requests.length,4);
 const series=await store.series('1');assert.deepEqual(series.map(r=>r.value),[0,2]);
 assert.deepEqual((await store.series('fora')).map(r=>r.value),[null,null]);assert.equal(f.requests.length,5);
});
test('falha de carga pode ser tentada novamente e arquivo adulterado é recusado',async()=>{
 const f=fixture(),store=createStore({model:M,fetcher:f.fetcher}),missing=f.files['mesh.gz'];delete f.files['mesh.gz'];
 await assert.rejects(store.load(),/indisponível/);f.files['mesh.gz']=missing;await store.load();
 f.files['2003.gz']=Buffer.alloc(f.manifest.years['2003'].bytes,1);await assert.rejects(store.year('2003'),/Integridade/);
});
test('rótulo parcial usa data da base; zero e fora da malha são distintos',()=>{
 const f=fixture();assert.equal(M.latestYear(f.manifest),'2026');assert.match(M.yearLabel(f.manifest,'2026'),/parcial até 06\/11\/2026/);
 assert.equal(M.municipalityValue([{code:'1',kind:'municipio'}],{annual:[0]},'1'),0);assert.equal(M.municipalityValue([],{annual:[]},'1'),null);
});
test('links antigos repassam ano e município e o destino liga a camada',()=>{
 for(const field of ['year','ano','focos_ano']){const target=M.legacyTarget('?'+field+'=2003&municipio=3550308','2026');const p=new URLSearchParams(target.split('?')[1]);assert.equal(p.get('focos'),'on');assert.equal(p.get('focos_ano'),'2003');assert.equal(p.get('municipio'),'3550308');}
 assert.equal(new URLSearchParams(M.legacyTarget('','2026').split('?')[1]).get('focos_ano'),'2026');
 const context={municipalities:new Set(['1']),nationalMunicipalities:new Set(['3550308']),categories:new Set(),carMunicipality:()=>'',coverage:{ufs:['AM']}};
 const decoded=S.decode('?focos=on&focos_ano=2003&municipio=3550308',context);assert.equal(decoded.state.focos,true);assert.equal(decoded.state.focos_ano,'2003');assert.equal(decoded.state.municipio,'3550308');
 assert.equal(S.decode('?focos=on&focos_ano=absurdo',context).state.focos_ano,'');
 const legacy=S.decode('?camadas=municipios,car,focos',context);assert.equal(legacy.state.focos,true);assert.ok(!legacy.state.camadas.includes('focos'));assert.ok(legacy.warnings.length);
});
function layerRuntime(store){
 const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,style:{},value:'',checked:false,textContent:'',setAttribute(){},addEventListener(){}});return nodes.get(id);};
 const errors=[],styles=[],panes=new Map(),environmentalFilters={opacity:.65};
 const layers=new Set(['car']),map={createPane:name=>{const pane={style:{}};panes.set(name,pane);return pane;},removeLayer:l=>layers.delete(l),fitBounds(){}};
 const context=vm.createContext({FocosBrasil:{createStore:()=>store},FocosModel:M,map,environmentalFilters,console:{error:(...args)=>errors.push(args)},document:{body:{classList:{toggle(){},remove(){}}}},$:s=>s==='#focos-municipality'?null:node(s),L:{canvas:()=>({}),geoJSON:(geo,options)=>({options,setStyle(fn){styles.push(fn(geo.features[0]));},addTo(){layers.add(this);return this;},getBounds:()=>[]})},mapPalette:{municipalities:{selectedColor:'#ff6b35'}},countyLayer:{setStyle(){}},countyStyle(){},state:{colorCounties:false},renderTerritory(){},renderMapLegend(){},mapHistoryReady:true,writeMapURL(){},selectedProperty:null,fmt:String,esc:String,toast(){},muni(){},HibamaMapState:S,mapCARCoverage:{ufs:['AM']}});
 vm.runInContext(fs.readFileSync(path.join(root,'dist/assets/focos-layer.js'),'utf8'),context);vm.runInContext('installNationalFocos()',context);
 return {node,layers,errors,styles,panes,environmentalFilters,run:s=>vm.runInContext(s,context)};
}
test('erro desmarca checkbox, remove camada e preserva CAR; desligar durante carga não reaparece',async()=>{
 const failed=layerRuntime({load:async()=>{throw Error('falha simulada');}});
 assert.equal(await failed.run('nationalFocos.setEnabled(true)'),false);assert.equal(failed.node('#layer-focos-brasil').checked,false);assert.equal(failed.node('#focos-status').textContent,'Não foi possível carregar os focos agora. Tente marcar a camada de novo.');assert.match(failed.errors[0][1].message,/falha simulada/);assert.deepEqual([...failed.layers],['car']);
 let resolve;const pending=layerRuntime({load:()=>new Promise(r=>resolve=r)});const task=pending.run('nationalFocos.setEnabled(true)');await pending.run('nationalFocos.setEnabled(false)');resolve({});await task;assert.deepEqual([...pending.layers],['car']);assert.equal(pending.node('#focos-controls').hidden,true);
});

test('períodos carregam apenas anos necessários e somam meses entre anos, sem mês provisório',async()=>{
 const f=fixture();
 const put=(name,value)=>{const bytes=zlib.gzipSync(JSON.stringify(value));f.files[name]=bytes;return {path:name,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};};
 f.manifest.default_period={start:'2003-02',end:'2004-01'};
 f.manifest.coverage['2004-01']={status:'complete'};f.manifest.coverage['2004-02']={status:'provisional'};
 f.manifest.years['2004']=put('2004.gz',{months:['complete','provisional',...Array(10).fill('unavailable')],monthly:[[3,100,...Array(10).fill(0)],[0,20,...Array(10).fill(0)],null],annual:[103,20,null]});
 f.files['manifesto.json']=Buffer.from(JSON.stringify(f.manifest));
 const store=createStore({model:M,fetcher:f.fetcher});
 const latest=await store.period('latest','2026','11');assert.equal(latest.periods.length,12);assert.deepEqual(latest.values,[3,0,null]);
 assert.equal(f.requests.some(p=>p.endsWith('2026.gz')),false);
 const month=await store.period('month','2004','2');assert.deepEqual(month.values,[100,20,null]);
 assert.deepEqual((await store.period('year','2004')).values,[103,20,null]);
 await assert.rejects(store.period('month','2004','3'),/sem dados/);
});
test('URL restaura os três modos, aceita links anuais antigos e elimina parâmetros inválidos',()=>{
 const context={municipalities:new Set(),categories:new Set(),carMunicipality:()=>'',coverage:{ufs:['AM']}};
 for(const mode of ['latest','year','month']){
  const state={...S.defaults(),focos:true,focos_ano:'2026',focos_periodo:mode,focos_mes:mode==='month'?'11':''};
  const decoded=S.decode(S.serialize(state),context);assert.deepEqual(decoded.state,state);assert.deepEqual(decoded.warnings,[]);
 }
 assert.equal(S.decode('?focos=on&focos_ano=2003',context).state.focos_periodo,'year');
 const invalid=S.decode('?focos=on&focos_periodo=invalido&focos_mes=13',context);assert.equal(invalid.state.focos_periodo,'latest');assert.equal(invalid.state.focos_mes,'');assert.equal(invalid.warnings.length,2);
 assert.equal(S.serialize({...S.defaults(),focos_periodo:'month',focos_mes:'11'}),'');
 const legacy=new URLSearchParams(M.legacyTarget('?period=month&year=2026&month=11','2026').split('?')[1]);assert.equal(legacy.get('focos_periodo'),'month');assert.equal(legacy.get('focos_mes'),'11');
});
test('camada usa opacidade atual na carga e ao mover slider, abaixo do CAR; período controla seletores',async()=>{
 const f=fixture();f.manifest.default_period={start:'2003-01',end:'2003-12'};
 f.files['manifesto.json']=Buffer.from(JSON.stringify(f.manifest));
 const runtime=layerRuntime(createStore({model:M,fetcher:f.fetcher}));
 assert.equal(await runtime.run("nationalFocos.setEnabled(true,{mode:'year',year:'2026'})"),true);
 const layer=[...runtime.layers].find(l=>l!=='car');assert.equal(layer.options.style({properties:{i:0}}).fillOpacity,.65);assert.equal(runtime.panes.get('focos-brasil').style.zIndex,350);
 runtime.environmentalFilters.opacity=.35;runtime.run('nationalFocos.applyOpacity()');assert.equal(runtime.styles.at(-1).fillOpacity,.35);
 const before=f.requests.length;
 await runtime.run("nationalFocos.setEnabled(true,{mode:'month',year:'2026',month:'1'})");assert.equal(runtime.node('#focos-month-label').hidden,false);assert.equal(runtime.run('nationalFocos.month'),'1');
 await runtime.run("nationalFocos.setEnabled(true,{mode:'month',month:'12'})");assert.equal(runtime.run('nationalFocos.month'),'1');
 await runtime.run("nationalFocos.setEnabled(true,{mode:'latest'})");assert.equal(runtime.node('#focos-year-label').hidden,true);assert.equal(runtime.node('#focos-month-label').hidden,true);assert.equal(runtime.run('nationalFocos.month'),'');
 assert.equal(f.requests.length,before+1); // só ano 2003, usado pelos 12 meses fechados
 assert.match(runtime.node('#focos-status').textContent,/Últimos 12 meses fechados/);
});
test('controle de opacidade atualiza focos e avisos completos ficam em Fontes, períodos e metodologia',()=>{
 const source=fs.readFileSync(path.join(root,'dist/assets/ambiental.js'),'utf8');let updated=0;
 const context=vm.createContext({nationalFocos:{applyOpacity:()=>updated++},document:{getElementById:()=>({textContent:''})}});
 vm.runInContext(source,context);vm.runInContext('applyEnvironmentalOpacity(42)',context);assert.equal(updated,1);assert.equal(vm.runInContext('environmentalFilters.opacity',context),.42);
 for(const text of ['Fontes, períodos e metodologia','Como ler este mapa','Origem e cobertura','não incêndios únicos ou hectares queimados','Zero detecções não comprova ausência de fogo','suas contagens não são comparáveis às desta série','AQUA_M-T','malha original IBGE 2025'])assert.ok(source.includes(text),text);
});

test('período provisório preserva a data-limite da página 2c-1 e o aviso de áreas operacionais',async()=>{
 const f=fixture();f.manifest.coverage['2026-01']={status:'provisional',maximum_utc:'2026-01-05T23:59:00Z'};
 f.files['manifesto.json']=Buffer.from(JSON.stringify(f.manifest));
 const runtime=layerRuntime(createStore({model:M,fetcher:f.fetcher}));
 await runtime.run("nationalFocos.setEnabled(true,{mode:'month',year:'2026',month:'1'})");
 assert.match(runtime.node('#focos-status').textContent,/2026-01 · UTC · PROVISÓRIO · até 2026-01-05/);
 assert.ok(fs.readFileSync(path.join(root,'dist/assets/ambiental.js'),'utf8').includes('Áreas operacionais: sem contagem.'));
});
