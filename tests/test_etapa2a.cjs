const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const visual = require('../dist/assets/map-visual.js');
const palette=visual.validatePalette(JSON.parse(fs.readFileSync(path.join(root,'dist/data/ambiental/paleta.json'),'utf8')));
const catalog=visual.bindCatalog(JSON.parse(fs.readFileSync(path.join(root,'dist/data/ambiental/catalogo.json'),'utf8')),palette);
const feature = category => ({properties:{category}});

test('paleta inválida gera erro claro e cores de camadas são distintas da seleção', () => {
  assert.equal(new Set(Object.values(palette.layers).map(s=>s.color)).size,6);
  assert.notEqual(palette.municipalities.selectedColor,palette.layers.ti.color);
  for(const mutate of [p=>delete p.layers.ti,p=>p.layers.focos.color=p.layers.anm.color,p=>p.municipalities.selectedColor=p.layers.ti.color,p=>p.cars.AT.color='inválida',p=>p.layers.ti.style.fillOpacity=.5]){
    const bad=structuredClone(palette);mutate(bad);
    assert.throws(()=>visual.validatePalette(bad),/Paleta visual inválida/);
  }
  assert.throws(()=>visual.bindCatalog({layers:[]},palette),/incompatível/);
});

test('municípios transparentes e clicáveis, com destaque sem preenchimento', () => {
  for (const selected of [true,false]) for (const hovered of [true,false]) {
    const style=visual.countyStyle(palette,selected,false,'#000000',hovered);
    assert.equal(style.fillOpacity,0);
    assert.equal(style.fill,true);
  }
  assert.equal(visual.countyStyle(palette,false,false,'').weight,1.5);
  assert.equal(visual.countyStyle(palette,true,false,'').weight,3);
  assert.notEqual(visual.countyStyle(palette,true,false,'').color,visual.countyStyle(palette,false,false,'').color);
  assert.ok(visual.countyStyle(palette,false,true,'').fillOpacity>0);
  assert.ok(visual.carStyle(palette,'AT').weight<1);
  assert.equal(visual.carStyle(palette,'AT').color,'#e4f5c9');
  assert.equal(new Set(['AT','PE','SU','CA'].map(s=>visual.carStyle(palette,s).color)).size,4);
  assert.equal(new Set(['AT','PE','SU','CA'].map(s=>visual.carStyle(palette,s).dashArray)).size,4);
  assert.ok(visual.carStyle(palette,'AT',true).weight>visual.carStyle(palette,'AT').weight);
});

test('contornos não recebem preenchimento em nenhuma opacidade; pontos mantêm a mesma regra', () => {
  for(const opacity of [.1,.65,1]) for(const spec of catalog.layers){
    const style=visual.environmentalStyle(spec,feature(''),opacity);
    assert.equal(style.opacity,opacity);
    if(['ti','anm','embargos'].includes(spec.id))assert.equal(style.fillOpacity,0);
    else assert.ok(style.fillOpacity>0);
    if(spec.id==='focos')assert.equal(style.fillOpacity,opacity);
  }
  assert.equal(new Set(catalog.layers.slice(0,3).map(s=>s.style.dashArray)).size,3);
});

test('todas as classes DETER dos 62 municípios têm estilo e rótulo; classe nova tem fallback', () => {
  const spec=catalog.layers.find(s=>s.id==='deter');
  const found=new Set();
  for(const code of Object.keys(catalog.counts_by_municipality)){
    const geo=JSON.parse(fs.readFileSync(path.join(root,`dist/data/ambiental/municipios/${code}.geojson`),'utf8'));
    for(const f of geo.features)if(f.properties.layer==='deter')found.add(f.properties.category);
  }
  for(const name of found){assert.ok(spec.style.categories[name]?.label,name);assert.equal(visual.environmentalStyle(spec,feature(name),.65).color,spec.style.categories[name].color);}
  assert.equal(found.size,8);
  assert.equal(visual.environmentalStyle(spec,feature('NOVA_CLASSE'),.65).color,spec.color);
});

function runtime(){
  const nodes=new Map();
  const node=key=>{if(!nodes.has(key))nodes.set(key,{textContent:'',hidden:false,innerHTML:''});return nodes.get(key);};
  const document={body:{dataset:{page:'map'}},querySelector:s=>node(s),querySelectorAll:()=>[],getElementById:id=>node('#'+id)};
  const context=vm.createContext({document,location:{search:'',pathname:'/mapa.html'},console,URLSearchParams,Intl,Map,Set,HibamaVisual:visual,AngelimActivities:require('../dist/assets/atividades.js'),qaPalette:palette,matchMedia:()=>({matches:false,addEventListener(){}}),MutationObserver:class{observe(){} disconnect(){}},ResizeObserver:class{observe(){}},setTimeout,clearTimeout});
  let app=fs.readFileSync(path.join(root,'dist/assets/app.js'),'utf8').replace(/\ninit\(\);/,'');
  vm.runInContext(app,context);
  vm.runInContext("mapPalette=qaPalette",context);
  vm.runInContext(fs.readFileSync(path.join(root,'dist/assets/ambiental.js'),'utf8'),context);
  return {context,node,run:script=>vm.runInContext(script,context)};
}

test('legenda inicia fechada e recolhe ao entrar na largura de celular', () => {
  const {context,node,run}=runtime();let change;
  context.matchMedia=()=>({matches:false,addEventListener:(_event,listener)=>change=listener});
  node('.map-legend').open=true;run('installLegend()');assert.equal(node('.map-legend').open,false);
  node('.map-legend').open=true;change({matches:true});assert.equal(node('.map-legend').open,false);
  assert.doesNotMatch(fs.readFileSync(path.join(root,'dist/assets/app.js'),'utf8'),/<details class="map-legend" open/);
});

test('Esri limita zoom nativo e apresenta falha, recuperação, troca de base e tentativa', () => {
  const {context,node,run}=runtime();
  const events={};let redraws=0,options;
  context.L={tileLayer:(_url,opts)=>{options=opts;return {on:(event,callback)=>events[event]=callback,redraw:()=>redraws++};}};
  run('imagery=satelliteLayer();installImageryStatus();');
  assert.equal(options.maxNativeZoom,16);assert.equal(options.maxZoom,19);
  assert.equal(options.errorTileUrl,'assets/tile-indisponivel.svg');
  const e={coords:{z:16,x:2,y:3},tile:{src:options.errorTileUrl}};
  events.tileerror(e);assert.match(node('#basemap-status').textContent,/indisponível/);assert.equal(node('#retry-imagery').hidden,false);
  events.tileload(e);assert.match(node('#basemap-status').textContent,/indisponível/);
  run("state.base='terrain';updateImageryStatus()");assert.match(node('#basemap-status').textContent,/OpenStreetMap/);assert.equal(node('#retry-imagery').hidden,true);
  run("state.base='satellite';updateImageryStatus()");
  node('#retry-imagery').onclick();assert.equal(redraws,1);
  events.tileerror(e);events.tileload({...e,tile:{src:'https://example.test/tile'}});
  assert.match(node('#basemap-status').textContent,/Data da imagem desconhecida/);assert.equal(node('#retry-imagery').hidden,true);
});

test('slider aplica o mesmo estilo do carregamento aos polígonos e pontos', () => {
  const {context,run}=runtime();context.data=catalog;context.styles={};
  run("environmentalCatalog=data;for(const spec of data.layers)environmentalLayers.set(spec.id,{setStyle:fn=>{styles[spec.id]=fn({properties:{category:'DEGRADACAO'}})}})");
  for(const value of [10,100,65]){
    run(`applyEnvironmentalOpacity('${value}')`);
    for(const spec of catalog.layers)assert.deepEqual(context.styles[spec.id],visual.environmentalStyle(spec,feature('DEGRADACAO'),value/100));
  }
});

test('desligar CAR remove também o destaque selecionado e sua legenda', () => {
  const {context,node,run}=runtime();context.removed=[];context.added=[];
  run("map={removeLayer:layer=>removed.push(layer.id)};carLayer={id:'cars',addTo:()=>added.push('cars')};propertyLayer={id:'selection',addTo:()=>added.push('selection')};state.showCars=false;setCarVisibility()");
  assert.deepEqual(context.removed,['cars','selection']);
  assert.doesNotMatch(node('#map-legend-content').innerHTML,/CAR selecionado/);
  run('state.showCars=true;setCarVisibility()');
  assert.deepEqual(context.added,['cars','selection']);
});

test('panes acima dos CARs não capturam o retângulo do mapa', () => {
  const {context,run}=runtime();context.panes={};
  run("map={createPane:name=>(panes[name]={style:{}})};createMapPanes()");
  for(const [name,z] of [['environmental-event',410],['environmental-outline',420],['environmental-point',430],['car-selection',450]]){
    assert.equal(context.panes[name].style.pointerEvents,'none');
    assert.equal(context.panes[name].style.zIndex,z);
  }
});

test('camadas e pontos ambientais usam SVG, mantendo apenas os desenhos interativos', async () => {
  const {context,run}=runtime();context.data=catalog;
  context.geo=JSON.parse(fs.readFileSync(path.join(root,'dist/data/ambiental/municipios/1302603.geojson'),'utf8'));
  const captured=[];
  context.L={svg:opts=>({type:'svg',...opts}),circleMarker:(_latlng,opts)=>({options:opts}),geoJSON:(geo,opts)=>{
    captured.push(opts);
    for(const f of geo.features)if(f.geometry.type==='Point')assert.equal(opts.pointToLayer(f,[0,0]).options.renderer,opts.renderer);
    return {addTo(){return this;}};
  }};
  run("map={removeLayer(){}};environmentalCatalog=data;selectedCode='1302603';fetchJSON=async()=>geo;for(const s of data.layers)environmentalEnabled.add(s.id)");
  await run('refreshEnvironmental()');
  assert.equal(captured.length,5);
  for(const options of captured){assert.equal(options.renderer.type,'svg');assert.equal(options.renderer.pane,options.pane);}
  assert.equal(new Set(captured.map(o=>o.renderer)).size,2);
  await run('refreshEnvironmental()');
  assert.equal(new Set(captured.map(o=>o.renderer)).size,2);
  assert.equal(captured.filter(o=>o.className==='environmental-outline-shape').length,6);
});

test('legenda e contagens acompanham filtros, município sem focos, desligamento e troca rápida', async () => {
  const {context,node,run}=runtime();
  context.data=catalog;
  context.geo=JSON.parse(fs.readFileSync(path.join(root,'dist/data/ambiental/municipios/1304237.geojson'),'utf8'));
  context.L={svg:opts=>opts,geoJSON:(_geo,opts)=>({addTo(){return this;},setStyle:opts.style})};
  run("map={removeLayer(){}};environmentalCatalog=data;selectedCode='1304237';fetchJSON=async()=>geo;for(const s of data.layers)environmentalEnabled.add(s.id)");
  await run('refreshEnvironmental()');
  assert.equal(run("environmentalVisible.filter(f=>f.properties.layer==='focos').length"),0);
  assert.equal(node('#count-deter').textContent,'76');
  assert.match(run('environmentalLegend()'),/Mineração/);
  run("environmentalFilters.category='MINERACAO'");await run('refreshEnvironmental()');
  const expected=context.geo.features.filter(f=>f.properties.layer==='deter'&&f.properties.category==='MINERACAO').length;
  assert.equal(node('#count-deter').textContent,String(expected));
  run("environmentalEnabled.clear()");await run('refreshEnvironmental()');assert.equal(run('environmentalVisible.length'),0);assert.equal(run('environmentalLegend()'),'');
  run("environmentalEnabled.add('ti');selectedCode='1304237';fetchJSON=()=>new Promise(resolve=>{globalThis.resolveOld=resolve})");
  const pending=run('refreshEnvironmental()');
  run("selectedCode='';");await run('refreshEnvironmental()');context.resolveOld(context.geo);await pending;
  assert.equal(run('environmentalVisible.length'),0);
  assert.match(node('#environmental-status').textContent,/Selecione um município/);
});
