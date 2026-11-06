'use strict';
// Contexto municipal: estas camadas não constituem análise individual do CAR.
let environmentalCatalog, environmentalVersion = 0;
const environmentalFilters={start:'',end:'',category:'',opacity:.65};
let environmentalVisible=[];
function matchesEnvironmental(feature){
 const p=feature.properties;
 if(p.layer==='deter' && !AngelimActivities.matchesClass(p.category,environmentalFilters.category))return false;
 if(!['prodes','deter'].includes(p.layer))return true;
 const start=environmentalFilters.start,end=environmentalFilters.end;
 if(!start&&!end)return true;
 if(p.layer==='prodes')return (!start||Number(p.year)>=Number(start.slice(0,4)))&&(!end||Number(p.year)<=Number(end.slice(0,4)));
 const date=String(p.date||'').slice(0,10);
 return !!date&&(!start||date>=start)&&(!end||date<=end);
}
const environmentalEnabled = new Set(), environmentalLayers = new Map();
const environmentalRenderers = new Map();
function environmentalRenderer(mode){
 if(!environmentalRenderers.has(mode))environmentalRenderers.set(mode,L.svg({pane:'environmental-'+mode}));
 return environmentalRenderers.get(mode);
}
function environmentalSymbol(spec,category){
 const style=HibamaVisual.environmentalStyle(spec,{properties:{category}},1);
 const shape=spec.style.mode==='point'?`<circle cx="14" cy="6" r="4"/>`:`<path d="M1 2H27V10H1Z"/>`;
 return `<svg class="environmental-symbol" viewBox="0 0 28 12" aria-hidden="true" style="color:${esc(style.color)}"><g stroke="currentColor" stroke-width="${style.weight}" fill="${style.fillOpacity?'currentColor':'none'}" fill-opacity="${style.fillOpacity}" stroke-dasharray="${esc(style.dashArray||'')}">${shape}</g></svg>`;
}
function environmentalLegend(){
 if(!environmentalCatalog)return '';
 let html='';
 for(const spec of environmentalCatalog.layers.filter(s=>s.id!=='focos')){
  if(!environmentalEnabled.has(spec.id))continue;
  const features=environmentalVisible.filter(f=>f.properties.layer===spec.id);
  const count=document.getElementById('count-'+spec.id)?.textContent||'—';
  html+=`<div class="legend-row">${environmentalSymbol(spec)}<span>${esc(spec.name)}</span><b>${esc(count)}</b></div>`;
  if(spec.style.categories){
   const counts=new Map();for(const f of features){const category=f.properties.category||'Sem classe';counts.set(category,(counts.get(category)||0)+1);}
   for(const [category,total] of counts){html+=`<div class="legend-row legend-category">${environmentalSymbol(spec,category)}<span>${esc(spec.style.categories[category]?.label||category)}</span><b>${fmt(total)}</b></div>`;}
  }
 }
 return html?'<strong>Contexto ambiental · feições</strong>'+html:'';
}
function applyEnvironmentalOpacity(value){
 environmentalFilters.opacity=Number(value)/100;
 document.getElementById('env-opacity-value').textContent=value+'%';
 if(typeof nationalFocos!=='undefined'&&nationalFocos)nationalFocos.applyOpacity();
 environmentalLayers.forEach((layer,id)=>{const spec=environmentalCatalog.layers.find(s=>s.id===id);layer.setStyle(feature=>HibamaVisual.environmentalStyle(spec,feature,environmentalFilters.opacity));});
}
async function refreshEnvironmental() {
  const version = ++environmentalVersion, code = selectedCode;
  environmentalLayers.forEach(layer => map.removeLayer(layer));
  environmentalLayers.clear();
  environmentalVisible=[];
  document.querySelectorAll('[id^=count-]').forEach(el=>el.textContent='—');
  renderMapLegend();
  if(typeof AngelimAgua!=='undefined')AngelimAgua.render(code);
  const status = document.getElementById('environmental-status');
  if (!status) return;
  if(environmentalFilters.start&&environmentalFilters.end&&environmentalFilters.start>environmentalFilters.end){status.textContent='A data inicial deve ser anterior à data final.';return;}
  if (!code) { status.textContent = 'Selecione um município para visualizar as camadas ambientais.'; return; }
  if (!environmentalEnabled.size) { status.textContent = 'Ative uma camada para consultar o contexto ambiental do município.'; return; }
  status.textContent = 'Carregando camadas ambientais…';
  try {
    const geo = await fetchJSON(`data/ambiental/municipios/${code}.geojson`);
    if (version !== environmentalVersion) return;
    for (const spec of environmentalCatalog.layers.filter(s=>s.id!=='focos')) {
      if (!environmentalEnabled.has(spec.id)) continue;
      const features = geo.features.filter(f => f.properties.layer === spec.id && matchesEnvironmental(f));
      environmentalVisible.push(...features);
      const badge=document.getElementById('count-'+spec.id);if(badge)badge.textContent=fmt(features.length);
      const pane='environmental-'+spec.style.mode,renderer=environmentalRenderer(spec.style.mode);
      const layer = L.geoJSON({type:'FeatureCollection',features}, {
        pane,renderer,bubblingMouseEvents:false,
        className:spec.style.mode==='outline'?'environmental-outline-shape':'',
        style: feature=>HibamaVisual.environmentalStyle(spec,feature,environmentalFilters.opacity),
        pointToLayer: (f,latlng) => L.circleMarker(latlng,{...HibamaVisual.environmentalStyle(spec,f,environmentalFilters.opacity),renderer,bubblingMouseEvents:false}),
        onEachFeature: (feature,item) => {
          const p=feature.properties;
          item.bindPopup(`<strong>${esc(spec.name)}</strong><br>${esc(p.title)}<br>${esc(p.category)}${p.date?'<br>Data: '+esc(p.date):''}<br><small>${esc(spec.note)}</small><br><a href="${esc(spec.url)}" target="_blank" rel="noopener noreferrer">Fonte: ${esc(spec.provider)}</a>`);
        }
      }).addTo(map);
      environmentalLayers.set(spec.id,layer);
    }
    renderMapLegend();
    status.textContent = 'Camadas carregadas. Contagens e classes na legenda do mapa. A ausência de feições na base não comprova ausência de ocorrências.';
  } catch (error) {
    if (version === environmentalVersion) status.textContent = 'Não foi possível carregar as camadas. Desative e ative uma camada para tentar novamente.';
    console.error(error);
  }
}
async function setupEnvironmental() {
  const panel = document.querySelector('.layer-panel');
  if (!panel) return;
  const group = document.createElement('div');
  group.className = 'layer-group';
  group.innerHTML = '<div class="panel-heading">CONTEXTO AMBIENTAL</div><p id="environmental-status" class="panel-note" role="status">Carregando catálogo ambiental…</p>';
  panel.insertBefore(group,panel.querySelector('.layer-info'));
  try {
    environmentalCatalog = HibamaVisual.bindCatalog(await fetchJSON('data/ambiental/catalogo.json?v=etapa2a-3'),mapPalette);
    for (const spec of environmentalCatalog.layers.filter(s=>s.id!=='focos')) {
      const label = document.createElement('label');
      label.className = 'layer-item';
      label.innerHTML = `<input type="checkbox" aria-label="${esc(spec.name)}" data-env="${esc(spec.id)}">${environmentalSymbol(spec)}<span>${esc(spec.name)}</span><b id="count-${esc(spec.id)}">—</b>`;
      label.title = `${spec.provider}. ${spec.note}`;
      label.querySelector('input').addEventListener('change',event => {
        event.target.checked ? environmentalEnabled.add(spec.id) : environmentalEnabled.delete(spec.id);
        refreshEnvironmental();
      });
      group.insertBefore(label,document.getElementById('environmental-status'));
    }
    const source = document.createElement('details');
    source.className = 'panel-note focos-methodology';
    source.innerHTML = `<summary>Fontes, períodos e metodologia</summary><a href="data/ambiental/catalogo.json" download>Baixar catálogo ambiental</a><h3>Como ler este mapa</h3><p>A cor representa detecções do satélite de referência, não incêndios únicos ou hectares queimados. Zero detecções não comprova ausência de fogo.</p><p>Anuais de referência INPE (2003–2025). Em 2026, AQUA_M-T filtrado dos arquivos mensais. “Todos os satélites” registra mais passagens e pode detectar o mesmo evento várias vezes; suas contagens não são comparáveis às desta série.</p><h3>Origem e cobertura</h3><p>Coordenadas atribuídas à malha original IBGE 2025. A geometria simplificada serve apenas à exibição. Áreas operacionais: sem contagem. CAR e demais camadas ambientais mantêm cobertura do Amazonas; não há cruzamento CAR nacional.</p><p>Últimos 12 meses fechados exclui o mês provisório. Ano usa os meses disponíveis; 2026 é parcial até a data da base. Mês permite consultar o período provisório, identificado no seletor. Datas em UTC. Os filtros de datas ambientais não se aplicam aos focos nacionais.</p><p><a href="https://terrabrasilis.dpi.inpe.br/queimadas/portal/" target="_blank" rel="noopener noreferrer">INPE · Programa Queimadas ↗</a> · <a href="https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/15774-malhas.html" target="_blank" rel="noopener noreferrer">IBGE · Malha Municipal ↗</a></p>`;
    group.append(source);
    installEnvironmentalFilters(group);
    const originalSelect = selectMunicipality;
    selectMunicipality = async function(...args) {
      await Promise.all([originalSelect(...args),refreshEnvironmental()]);
    };
    await refreshEnvironmental();
  } catch (error) {
    document.getElementById('environmental-status').textContent = error.message || 'Catálogo ambiental indisponível. Recarregue a página para tentar novamente.';
    console.error(error);
  }
}
function installEnvironmentalFilters(group){
 document.querySelectorAll('[data-pending]').forEach(el=>el.closest('.layer-group')?.remove());
 const metric=document.getElementById('map-metric');if(metric)metric.remove();
 group.insertAdjacentHTML('beforebegin',`<section class="env-filters"><h3>Refinar a análise</h3><p>Período aplicado a PRODES e DETER. Limites territoriais e registros administrativos permanecem visíveis.</p><div class="env-dates"><label>De<input id="env-start" type="date" max="2026-11-05"></label><label>Até<input id="env-end" type="date" max="2026-11-05"></label></div><p>PRODES é filtrado pelo ano de referência.</p><label>Classe do alerta<select id="env-category"><option value="">Todas as classes DETER</option></select></label><label>Opacidade <output id="env-opacity-value">65%</output><input id="env-opacity" type="range" min="10" max="100" value="65"></label><div class="env-actions"><button class="btn btn-small" id="env-reset">Limpar filtros</button><button class="btn btn-small" id="env-export">Exportar seleção</button></div></section>`);
 const categories=environmentalCatalog.layers.find(spec=>spec.id==='deter').style.categories;
 document.getElementById('env-category').insertAdjacentHTML('beforeend',Object.entries(categories).map(([id,spec])=>`<option value="${esc(id)}">${esc(spec.label)}</option>`).join(''));
 document.getElementById('env-category').insertAdjacentHTML('beforeend',Object.entries(AngelimActivities.groups).map(([id,spec])=>`<option value="${esc(id)}">${esc(spec.label)}</option>`).join(''));
 ['start','end','category'].forEach(key=>document.getElementById('env-'+key).addEventListener('change',e=>{environmentalFilters[key]=e.target.value;refreshEnvironmental();}));
 document.getElementById('env-opacity').oninput=e=>applyEnvironmentalOpacity(e.target.value);
 document.getElementById('env-reset').onclick=()=>{environmentalFilters.start='';environmentalFilters.end='';environmentalFilters.category='';['start','end','category'].forEach(key=>document.getElementById('env-'+key).value='');refreshEnvironmental();};
 document.getElementById('env-export').onclick=()=>{if(!selectedCode){toast('Selecione um município.');return;}openMunicipalityReport(selectedCode);};
 group.insertAdjacentHTML('afterend',`<details class="env-filters"><summary>Imagens • Google Earth Engine</summary><p>Sentinel-2: cor natural ou vegetação (NDVI). Use as datas acima para definir um mosaico de até 366 dias.</p><label>Visualização<select id="ee-product"><option value="rgb">Cor natural • 10 m</option><option value="ndvi">Vegetação • NDVI</option></select></label><label>Nuvens por cena: até <output id="ee-cloud-value">30%</output><input type="range" id="ee-cloud" min="0" max="100" value="30"></label><button class="btn btn-small" id="ee-load">Carregar imagens</button><button class="btn btn-small" id="ee-remove">Remover imagem</button><p id="ee-status" role="status">Requer conexão com sua conta Earth Engine.</p></details>`);
 document.getElementById('ee-cloud').oninput=e=>document.getElementById('ee-cloud-value').textContent=e.target.value+'%';
 let eeLayer,eeVersion=0;
 document.getElementById('ee-remove').onclick=()=>{eeVersion++;if(eeLayer)map.removeLayer(eeLayer);eeLayer=null;document.getElementById('ee-status').textContent='Imagem removida.';};
 const clearOnChange=selectMunicipality;
 selectMunicipality=function(...args){document.getElementById('ee-remove').click();return clearOnChange(...args);};
 document.getElementById('ee-load').onclick=async()=>{
 const output=document.getElementById('ee-status'),version=++eeVersion;
 if(!selectedCode||!environmentalFilters.start||!environmentalFilters.end){output.textContent='Selecione um município e informe as duas datas.';return;}
 output.textContent='Consultando cenas Sentinel-2…';
 try{const q=new URLSearchParams({municipio:selectedCode,start:environmentalFilters.start,end:environmentalFilters.end,product:document.getElementById('ee-product').value,cloud:document.getElementById('ee-cloud').value});const response=await fetch('/api/earth-engine?'+q);if(!(response.headers.get('content-type')||'').includes('application/json'))throw Error('Serviço de imagens Sentinel-2 indisponível no momento. Tente novamente em instantes.');const data=await response.json();if(!response.ok)throw Error(data.error||'Falha na consulta Earth Engine.');if(version!==eeVersion)return;if(eeLayer)map.removeLayer(eeLayer);eeLayer=L.tileLayer(data.url,{attribution:'Google Earth Engine · Copernicus Sentinel-2',maxNativeZoom:14,maxZoom:19,opacity:.85}).addTo(map);output.textContent=data.count+' cenas • '+data.start+' a '+data.end+'. Mosaico mediano com máscara de nuvens. NDVI: −1 a 1 (marrom → verde).';}catch(error){if(version===eeVersion)output.textContent=error.message;}
 };
 new ResizeObserver(()=>map.invalidateSize({pan:false})).observe(document.getElementById('main-map'));
}
