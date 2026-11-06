/* Etapa 5a: busca e histórico; não adiciona camadas ao mapa principal. */
'use strict';
let mapHistoryReady=false,localMunicipalities=[],localMunicipalityMesh,mapLookupVersion=0,mapRestoreVersion=0,searchIndexStatus='loading',mapCARCoverage;
const currentMapState=(car=selectedProperty?.code||'')=>({
 municipio:nationalFocos?.enabled?(nationalFocos.selection||selectedCode):selectedCode,car,camadas:HibamaMapState.layerIds.filter(id=>id==='municipios'?state.showCounties:id==='car'?state.showCars:environmentalEnabled.has(id)),
 inicio:environmentalFilters.start,fim:environmentalFilters.end,classe:environmentalFilters.category,
 opacidade:Math.round(environmentalFilters.opacity*100),base:state.base,colorir:state.colorCounties,focos:nationalFocos?.enabled||false,focos_ano:nationalFocos?.year||'',focos_periodo:nationalFocos?.mode||'latest',focos_mes:nationalFocos?.month||''
});
function writeMapURL(car=selectedProperty?.code||'',options={}){
 if(!mapHistoryReady||options.history===false)return;
 const target=location.pathname+HibamaMapState.serialize(currentMapState(car));
 if(location.pathname+location.search!==target)history[options.replace?'replaceState':'pushState']({hibama:true},'',target);
}
function mapURLContext(){return {municipalities:new Set(catalog.municipalities.map(m=>m.code)),categories:new Set([...Object.keys(mapPalette.layers.deter.style.categories),...Object.keys(AngelimActivities.groups)]),carMunicipality:municipalityForCar,coverage:mapCARCoverage,nationalMunicipalities:new Set(localMunicipalities.map(m=>m.code))};}
async function restoreMapURL(){
 const version=++mapRestoreVersion;
 const {state:next,warnings}=HibamaMapState.decode(location.search,mapURLContext());
 if(warnings.length)history.replaceState({hibama:true},'',location.pathname+HibamaMapState.serialize(next));
 await applyMapFilters(next);
 if(next.car&&!selectedProperty)warnings.push('CAR não encontrado na base local; seleção removida.');
 if(warnings.length&&version===mapRestoreVersion)toast(warnings.join(' '));
}
async function applyMapFilters(next){
 mapLookupVersion++;
 state.showCounties=next.camadas.includes('municipios');state.showCars=next.camadas.includes('car');state.colorCounties=next.colorir;
 $('#layer-counties').checked=state.showCounties;$('#layer-cars').checked=state.showCars;$('#color-counties').checked=state.colorCounties;
 state.showCounties?countyLayer.addTo(map):map.removeLayer(countyLayer);
 environmentalEnabled.clear();for(const id of next.camadas)if(!['municipios','car'].includes(id))environmentalEnabled.add(id);
 document.querySelectorAll('[data-env]').forEach(el=>el.checked=environmentalEnabled.has(el.dataset.env));
 for(const [key,value] of [['start',next.inicio],['end',next.fim],['category',next.classe]]){environmentalFilters[key]=value;$('#env-'+key).value=value;}
 $('#env-opacity').value=next.opacidade;applyEnvironmentalOpacity(next.opacidade);
 state.base=next.base;map.removeLayer(imagery);map.removeLayer(terrain);(state.base==='satellite'?imagery:terrain).addTo(map);
 $('.map-canvas-wrap').classList.toggle('satellite',state.base==='satellite');$$('[data-base]').forEach(b=>b.classList.toggle('active',b.dataset.base===state.base));updateImageryStatus();
 $('#map-search').value='';$('#search-notice').hidden=true;$('#map-search').dispatchEvent(new Event('input'));
 await selectMunicipality(muni(next.municipio)?next.municipio:'',next.car,{history:false,fit:!next.focos});
 await nationalFocos.setEnabled(next.focos,{year:next.focos_ano,mode:next.focos_periodo,month:next.focos_mes});
 if(nationalFocos.enabled){nationalFocos.select(next.municipio);renderTerritory();if(next.municipio&&!next.car)nationalFocos.fitSelection();else if(!next.municipio)nationalFocos.fit();}
 if(next.focos&&(!nationalFocos.enabled||nationalFocos.year!==next.focos_ano||nationalFocos.mode!==next.focos_periodo||nationalFocos.month!==next.focos_mes))writeMapURL(selectedProperty?.code||'',{replace:true});
}
function outsideMunicipality(m){
 const notice=$('#search-notice');notice.hidden=false;
 const message=HibamaMapState.coverageMessage(mapCARCoverage);
 notice.innerHTML=`<strong>${esc(m.name)} · ${esc(m.uf)}</strong><br>${esc(message)} <a href="focos.html?municipio=${m.code}">Abrir em Focos Brasil</a>`;
 toast(`${m.name} · ${m.uf}. ${message}`);
}
function chooseLocalMunicipality(m){
 mapLookupVersion++;$('#map-search').value=m.name+' · '+m.uf;$('#search-notice').hidden=true;
 if(nationalFocos?.enabled)selectNationalMunicipality(m.code);else if(HibamaMapState.supportsUF(mapCARCoverage,m.uf))selectMunicipality(m.code);else outsideMunicipality(m);
}
function searchLocalTerritory(value){
 const car=value.trim().toUpperCase().replace(/\s/g,'');
 if(HibamaMapState.carUF(car)){if(HibamaMapState.isCarCode(car,mapCARCoverage))selectMunicipality(municipalityForCar(car),car);else toast(HibamaMapState.coverageMessage(mapCARCoverage));return;}
 const matches=HibamaMapState.search(localMunicipalities,value,12,mapCARCoverage);
 const exact=matches.find(m=>HibamaMapState.normalize(m.name)===HibamaMapState.normalize(value));
 if(exact||matches.length===1)chooseLocalMunicipality(exact||matches[0]);
 else toast(matches.length?'Escolha um município na lista da busca.':'Nenhum resultado para município ou número do CAR.');
}
function installAutocomplete(){
 const input=$('#map-search'),wrap=input.closest('.search-input');wrap.classList.add('territory-search');input.removeAttribute('list');$('#municipality-names')?.remove();
 input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');input.setAttribute('aria-expanded','false');input.setAttribute('aria-controls','territory-options');input.setAttribute('autocomplete','off');
 wrap.insertAdjacentHTML('beforeend','<div id="territory-options" class="territory-options" role="listbox" aria-label="Resultados de municípios" hidden></div>');
 wrap.insertAdjacentHTML('afterend','<div id="search-notice" class="search-notice" role="status" hidden></div>');
 const list=$('#territory-options');let items=[],active=-1;
 const close=()=>{list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1;};
 const activate=index=>{active=index;list.querySelectorAll('[role=option]').forEach((el,i)=>el.setAttribute('aria-selected',String(i===active)));if(active>=0){input.setAttribute('aria-activedescendant','territory-option-'+active);list.querySelector('#territory-option-'+active)?.scrollIntoView({block:'nearest'});}else input.removeAttribute('aria-activedescendant');};
 const pick=index=>{const item=items[index];if(!item)return;close();if(item.car)searchLocalTerritory(item.car);else chooseLocalMunicipality(item);};
 const render=()=>{
  $('#search-notice').hidden=true;const query=input.value.trim();active=-1;input.removeAttribute('aria-activedescendant');
  if(!query){close();return;}
  if(searchIndexStatus==='loading'){items=[];list.innerHTML='<div role="status">Carregando índice municipal local…</div>';list.hidden=false;input.setAttribute('aria-expanded','true');return;}
  const car=query.toUpperCase().replace(/\s/g,'');
  if(searchIndexStatus==='error'&&!HibamaMapState.carUF(car)){items=[];list.innerHTML='<div role="status">Índice municipal local indisponível. Recarregue a página.</div>';list.hidden=false;input.setAttribute('aria-expanded','true');return;}
  items=HibamaMapState.isCarCode(car,mapCARCoverage)?[{car}]:HibamaMapState.search(localMunicipalities,query,12,mapCARCoverage);
  list.innerHTML=items.length?items.map((m,i)=>`<button type="button" role="option" aria-selected="false" id="territory-option-${i}">${m.car?'Consultar CAR '+esc(m.car):esc(m.name)+' <span>'+esc(m.uf)+'</span>'}</button>`).join(''):'<div role="status">Nenhum resultado. Tente outro nome, trecho ou código CAR.</div>';
  list.hidden=false;input.setAttribute('aria-expanded','true');
  list.querySelectorAll('[role=option]').forEach((el,i)=>{el.addEventListener('pointerdown',e=>e.preventDefault());el.addEventListener('click',()=>pick(i));});
 };
 input.addEventListener('input',render);input.addEventListener('focus',()=>{if(input.value)render();});
 input.addEventListener('keydown',event=>{
  if(event.key==='Escape'){event.preventDefault();close();return;}
  if(['ArrowDown','ArrowUp'].includes(event.key)){event.preventDefault();if(list.hidden)render();if(items.length)activate(active<0?(event.key==='ArrowDown'?0:items.length-1):(active+(event.key==='ArrowDown'?1:-1)+items.length)%items.length);}
  if(event.key==='Enter'){event.preventDefault();if(items.length&&!list.hidden)pick(active>=0?active:0);else {close();searchLocalTerritory(input.value);}}
 });
 input.addEventListener('blur',()=>{setTimeout(()=>{if(!wrap.contains(document.activeElement))close();},0);});
 document.addEventListener('pointerdown',event=>{if(!wrap.contains(event.target))close();});
}
async function loadSearchIndex(){
 const data=await fetchJSON('data/busca-municipios.json?v=etapa5a');
 if(data.version!==1||data.mesh_year!==2025||data.municipalities?.length!==5571)throw Error('Índice municipal local inválido. Execute tools/preparar_busca.py.');
 localMunicipalities=data.municipalities.map(([code,name,uf,bounds])=>({code,name,uf,bounds}));
}
async function municipalityAt(latlng){
 // A malha da base cadastral já está em memória; evita baixar a malha nacional neste caso.
 if(nationalFocos?.enabled&&nationalFocos.data){const hit=nationalFocos.data.geo.features.find(f=>HibamaMapState.covers(f.geometry,latlng.lng,latlng.lat));if(hit)return nationalFocos.data.index[hit.properties.i];}
 const local=municipalitiesGeo.features.filter(f=>HibamaMapState.covers(f.geometry,latlng.lng,latlng.lat)).sort((a,b)=>a.properties.code.localeCompare(b.properties.code));
 if(local.length){const m=muni(local[0].properties.code),uf=localMunicipalities.find(item=>item.code===m.code)?.uf||catalog.uf;return {code:m.code,name:m.name,uf};}
 const candidates=localMunicipalities.filter(m=>latlng.lng>=m.bounds[0]&&latlng.lng<=m.bounds[2]&&latlng.lat>=m.bounds[1]&&latlng.lat<=m.bounds[3]);
 if(!candidates.length)return null;
 if(!localMunicipalityMesh){localMunicipalityMesh=(async()=>{
  const manifest=await fetchJSON('data/focos-brasil/manifesto.json');const descriptor=manifest.mesh;
  const response=await fetch('data/focos-brasil/'+descriptor.path);if(!response.ok)throw Error('Malha nacional local indisponível. Restaure os produtos da 2c-1.');
  const bytes=await response.arrayBuffer();if(bytes.byteLength!==descriptor.bytes)throw Error('Malha nacional local com tamanho inválido.');
  if(crypto.subtle){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==descriptor.sha256)throw Error('Malha nacional local com integridade inválida.');}
  if(!window.DecompressionStream)throw Error('Seu navegador precisa de suporte a gzip para consultar a malha nacional local.');
  return (await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).json()).features;
 })().catch(error=>{localMunicipalityMesh=null;throw error;});}
 const geometryByCode=new Map((await localMunicipalityMesh).map(f=>[f.id,f.geometry]));
 return candidates.filter(m=>HibamaMapState.covers(geometryByCode.get(m.code),latlng.lng,latlng.lat)).sort((a,b)=>a.code.localeCompare(b.code))[0]||null;
}
async function initializeMapTools(){
 const controls=[$('.map-toolbar'),$('.layer-panel')];
 controls.forEach(el=>el.inert=true);$('#main-map').setAttribute('aria-busy','true');
 try {
 mapCARCoverage=HibamaMapState.coverage(catalog);
 installAutocomplete();
 const searchReady=loadSearchIndex().then(()=>{searchIndexStatus='ready';if($('#map-search').value)$('#map-search').dispatchEvent(new Event('input'));}).catch(error=>{searchIndexStatus='error';toast(error.message||'Índice municipal local indisponível. Execute tools/preparar_busca.py.');});
 await setupEnvironmental();
 installNationalFocos();
 AngelimActivities.install({panel:$('.layer-panel'),getState:currentMapState,hasMunicipality:code=>!!muni(code),apply:async next=>{await applyMapFilters(next);writeMapURL();}});
 mapHistoryReady=true;
 for(const selector of ['#layer-counties','#layer-cars','#color-counties','[data-env]','#env-start','#env-end','#env-category','#env-opacity'])document.querySelectorAll(selector).forEach(el=>el.addEventListener('change',()=>writeMapURL()));
 document.querySelectorAll('[data-base]').forEach(el=>el.addEventListener('click',()=>writeMapURL()));
 $('#env-reset').onclick=async()=>{await applyMapFilters(HibamaMapState.defaults());writeMapURL();};
 window.addEventListener('popstate',()=>restoreMapURL().catch(error=>toast(error.message)));
 map.on('click',async event=>{if(event.originalEvent?.target?.closest('.leaflet-control,button,a,input,select'))return;const version=++mapLookupVersion,selection=displayToken;try{await searchReady;const m=await municipalityAt(event.latlng);if(version!==mapLookupVersion||selection!==displayToken)return;
  if(!m){L.popup().setLatLng(event.latlng).setContent('Nenhum município encontrado na malha local para este ponto.').openOn(map);return;}
  if(nationalFocos.enabled){await selectNationalMunicipality(m.code);return;}
  if(HibamaMapState.supportsUF(mapCARCoverage,m.uf)){await selectMunicipality(m.code);if(version!==mapLookupVersion)return;L.popup().setLatLng(event.latlng).setContent(`<strong>${esc(m.name)} · ${esc(m.uf)}</strong><br>Município identificado pela malha local IBGE 2025.`).openOn(map);}
  else {outsideMunicipality(m);L.popup().setLatLng(event.latlng).setContent(`<strong>${esc(m.name)} · ${esc(m.uf)}</strong><br>${esc(HibamaMapState.coverageMessage(mapCARCoverage))}<br><a href="focos.html?municipio=${m.code}">Abrir em Focos Brasil</a>`).openOn(map);}
 }catch(error){if(version===mapLookupVersion)toast(error.message);}});
 await searchReady;await restoreMapURL();
 } finally {
  controls.forEach(el=>el.inert=false);$('#main-map').setAttribute('aria-busy','false');
 }
}
