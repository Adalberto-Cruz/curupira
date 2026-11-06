'use strict';
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const fmt = (v, digits=0) => new Intl.NumberFormat('pt-BR',{maximumFractionDigits:digits}).format(v ?? 0);
const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm = v => String(v ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
const statusInfo = {AT:{name:'Ativo',plural:'Ativos',color:'#4d7957'},PE:{name:'Pendente',plural:'Pendentes',color:'#d6ad65'},SU:{name:'Suspenso',plural:'Suspensos',color:'#b8875e'},CA:{name:'Cancelado',plural:'Cancelados',color:'#a9afa0'}};
const typeNames = {IRU:'Imóvel rural',AST:'Assentamento',PCT:'Povos e comunidades tradicionais'};
const paths = {
 arrow:'M4 12h16m-6-6 6 6-6 6', chevron:'m9 5 7 7-7 7', search:'M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
 map:'m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2Zm6-2v16M15 5v16', layers:'m12 2 10 6-10 6L2 8Zm-9 11 9 5 9-5M3 18l9 5 9-5',
 file:'M14 2H5v20h14V7Zm0 0v6h5M8 12h8M8 16h8', download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',
 check:'m5 12 4 4L19 6', shield:'m12 2 9 4v6c0 5-9 10-9 10s-9-5-9-10V6Zm-4 10 3 3 5-6',
 clock:'M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0', globe:'M2 12h20M12 2c6 6 6 14 0 20-6-6-6-14 0-20M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 pin:'M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
 external:'M14 3h7v7m0-7L10 14M10 3H3v18h18v-7', info:'M12 11v6m0-10v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
 close:'m5 5 14 14M5 19 19 5', filter:'M3 5h18M6 12h12M9 19h6', database:'M21 6c0 2-4 4-9 4S3 8 3 6s4-4 9-4 9 2 9 4Zm0 0v12c0 2-4 4-9 4s-9-2-9-4V6m0 6c0 2 4 4 9 4s9-2 9-4',
 focus:'M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M9 12h6m-3-3v6', print:'M6 8V2h12v6M6 17H3V8h18v9h-3M6 14h12v8H6Zm12-3h.01',
 leaf:'M4 18C1 7 9 3 21 3c0 12-7 18-17 15Zm0 4L17 7', eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name]||paths.info}"/></svg>`;
const brand = () => HibamaHeader.brand();
const PAGE = document.body.dataset.page;
const params = new URLSearchParams(location.search);
let mapPalette, catalog, municipalitiesGeo, carMunicipalityIndex={}, selectedCode=params.get('municipio') || params.get('car')?.split('-')[1] || '', selectedProperty=null;
let map, countyLayer, carLayer, propertyLayer, imagery, terrain, displayToken=0, tablePage=0, currentTab='cadastros';
const cache=new Map();
const state={query:'',status:'',showCars:true,showCounties:true,base:'satellite',metric:'cadastros',colorCounties:false};
async function fetchJSON(url){if(cache.has(url))return cache.get(url);const p=fetch(url).then(r=>{if(!r.ok)throw new Error('Não foi possível carregar esta base. Tente novamente.');return r.json();});cache.set(url,p);try{return await p;}catch(e){cache.delete(url);throw e;}}
const muni = code => catalog.municipalities.find(m=>m.code===code);
const recordsFor = code => fetchJSON(`data/cadastros/${code}.json`);
const municipalityForCar = code => carMunicipalityIndex[code] || code.split('-')[1];
const date = v => v ? new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo'}).format(new Date(v)) : 'Não informado';
const getStatuses = () => selectedCode ? muni(selectedCode).statuses : catalog.statuses;
const getCount = () => selectedCode ? muni(selectedCode).count : catalog.total;
const getName = () => selectedCode ? muni(selectedCode).name : 'Amazonas';
const statusPill = s => {const c=statusInfo[s]||{name:s,color:'#8a967a'};return `<span class="pill" style="background:${c.color}18;color:${c.color}"><span class="dot" style="background:${c.color};width:4px;height:4px"></span>${esc(c.name)}</span>`;};
function toast(message){const t=$('#toast');t.textContent=message;t.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('show'),5000);}
function header(){return HibamaHeader.render(PAGE);}
function footer(){return `<footer class="footer">${brand()}<p>Inteligência territorial com dados públicos.<br>Plataforma independente. Não substitui a análise do órgão ambiental.<br>Projeto open source desenvolvido para o hackathon Reboot the Earth. Não é produto oficial da ONU, nem laudo ou documento oficial.</p><div class="footer-links"><a href="dados.html?aba=fontes">Fontes e metodologia</a><a href="https://github.com/Adalberto-Cruz/curupira" target="_blank" rel="noopener">Código no GitHub</a><a href="data/proveniencia.json" download>Rastreabilidade ${icon('external')}</a></div></footer>`;}
function municipalityOptions(allLabel='Todos os municípios'){return `<option value="">${allLabel}</option>`+catalog.municipalities.map(m=>`<option value="${m.code}" ${m.code===selectedCode?'selected':''}>${esc(m.name)}</option>`).join('');}
function home(){
 $('#app').innerHTML=header()+`<main><section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="dash"></span>INTELIGÊNCIA TERRITORIAL · AMAZÔNIA</div><h1>O território,<br>em <em>evidência.</em></h1><p>Conecte imagens, cadastros e dados ambientais.<br>Uma nova perspectiva para conhecer a floresta<br class="desktop-break"> e fundamentar cada análise.</p><div class="hero-buttons"><a class="btn btn-primary" href="mapa.html">Explorar o mapa ${icon('arrow')}</a><a class="btn" href="dados.html">Consultar CAR ${icon('search')}</a><a class="btn" href="https://github.com/Adalberto-Cruz/curupira" target="_blank" rel="noopener">Código no GitHub</a></div><div class="hero-note"><span>${icon('globe')} Dados públicos e rastreáveis</span><span>${icon('shield')} Evidências para auditoria</span></div></div><div class="hero-visual"><div id="hero-map" class="hero-map" role="img" aria-label="Mapa de satélite do Amazonas e limites municipais"></div><div class="map-tag"><span class="dot"></span>AMAZONAS, BRASIL</div><div class="map-coordinate">03°06′ S &nbsp; 60°01′ W</div><div class="visual-label">AMAZONAS</div><a class="map-floating" href="mapa.html"><span class="floating-icon">${icon('layers')}</span><div><strong>Uma visão. Todo o território.</strong><p>Explore os 62 municípios do Amazonas.</p></div><span class="pill"><span class="dot"></span>Base disponível</span></a></div></section><section class="stats-strip" aria-label="Cobertura da base"><div class="stats-label">Dados que aproximam<br>o território da sua análise.</div><div class="stats-item"><strong>62</strong><span>municípios mapeados</span></div><div class="stats-item"><strong>${fmt(catalog.total)}</strong><span>registros públicos do CAR</span></div><div class="stats-item"><strong>100%</strong><span>dos municípios com registros na base</span></div></section><section class="section"><div class="section-heading"><div><div class="eyebrow"><span class="dash"></span>DO MAPA À EVIDÊNCIA</div><h2>Entenda o contexto.<br>Aprofunde a análise.</h2></div><p>Comece pelo município, encontre o imóvel e reúna informações com origem, data e limites de interpretação.</p></div><div class="feature-grid"><article class="feature"><div class="feature-top">${icon('map')}<span>01 / EXPLORAR</span></div><h3>O Amazonas em cada detalhe.</h3><p>Navegue pelo território, compare a distribuição dos cadastros e explore os perímetros declarados no CAR.</p><a href="mapa.html">Abrir mapa interativo ${icon('arrow')}</a></article><article class="feature"><div class="feature-top">${icon('database')}<span>02 / INVESTIGAR</span></div><h3>O cadastro encontra o território.</h3><p>Consulte situação, condição de análise e dados declarados. Acesse a geometria e a fonte de cada registro.</p><a href="dados.html">Consultar dados do CAR ${icon('arrow')}</a></article><article class="feature"><div class="feature-top">${icon('file')}<span>03 / DOCUMENTAR</span></div><h3>Cada análise deixa um registro.</h3><p>Organize um dossiê cadastral com fontes, observações e informações pendentes de verificação ambiental.</p><a href="dados.html">Preparar um dossiê ${icon('arrow')}</a></article></div></section><div class="process-band"><div class="label">Um caminho claro<br><strong>para decisões fundamentadas.</strong></div><div class="process-step"><b>01</b> Selecione o município</div>${icon('arrow')}<div class="process-step"><b>02</b> Consulte o imóvel</div>${icon('arrow')}<div class="process-step"><b>03</b> Reúna as evidências</div></div></main>`+footer();
 const hmap=L.map('hero-map',{zoomControl:false,attributionControl:true,scrollWheelZoom:false,dragging:false,doubleClickZoom:false,boxZoom:false,keyboard:false,touchZoom:false,zoomSnap:.1});
 satelliteLayer().addTo(hmap);
 L.geoJSON(municipalitiesGeo,{style:{color:mapPalette.municipalities.color,weight:1.5,fillOpacity:0},interactive:false}).addTo(hmap);
 hmap.fitBounds([[-9.8,-73.9],[2.3,-56]],{padding:[5,5]});
}
function satelliteLayer(){return L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'Imagens © Esri, Maxar, Earthstar Geographics · Data desconhecida',maxNativeZoom:16,maxZoom:19,errorTileUrl:'assets/tile-indisponivel.svg',crossOrigin:true});}
function colorCount(n){const colors=mapPalette.municipalities.countScale;return colors[Math.min(5,Math.floor(Math.sqrt(n/7200)*6))];}
function countyStyle(f,hovered=false){const m=muni(f.properties.code);return HibamaVisual.countyStyle(mapPalette,f.properties.code===selectedCode,state.colorCounties&&!(typeof nationalFocos!=='undefined'&&nationalFocos?.enabled),colorCount(state.status?(m.statuses[state.status]||0):m.count),hovered);}
let failedImageryTiles = new Set();
function updateImageryStatus(){
 const output=$('#basemap-status');if(!output)return;
 const satellite=state.base==='satellite';
 output.textContent=!satellite?'OpenStreetMap · mapa de ruas.':failedImageryTiles.size?'Esri · Imagem indisponível em parte da vista. Tente novamente, afaste o zoom ou use Ruas. Data da imagem desconhecida.':'Esri · Data da imagem desconhecida. Acima do zoom 16, imagem ampliada.';
 $('#retry-imagery').hidden=!satellite||!failedImageryTiles.size;
}
function installImageryStatus(){
 const key=e=>`${e.coords.z}/${e.coords.x}/${e.coords.y}`;
 imagery.on('tileerror',e=>{failedImageryTiles.add(key(e));updateImageryStatus();});
 imagery.on('tileload',e=>{if(!e.tile.src.includes('tile-indisponivel.svg'))failedImageryTiles.delete(key(e));updateImageryStatus();});
 imagery.on('tileunload',e=>{failedImageryTiles.delete(key(e));updateImageryStatus();});
 $('#retry-imagery').onclick=()=>{failedImageryTiles.clear();imagery.redraw();updateImageryStatus();};
}
function legendLine(label,color,count,extra=''){
 return `<div class="legend-row"><svg viewBox="0 0 28 12" aria-hidden="true"><path d="M1 6H27" stroke="${esc(color)}" stroke-width="2" ${extra}/></svg><span>${esc(label)}</span><b>${count===null?'':fmt(count)}</b></div>`;
}
function renderMapLegend(){
 const target=$('#map-legend-content');if(!target)return;
 let html='';
 if(state.showCounties){html+=legendLine('Limites municipais',mapPalette.municipalities.color,62)+legendLine('Município selecionado',mapPalette.municipalities.selectedColor,selectedCode?1:0);if(state.colorCounties)html+=`<div class="legend-counts"><strong>Registros CAR por município</strong><div class="legend-gradient" style="background:linear-gradient(90deg,${mapPalette.municipalities.countScale.join(',')})"></div><div class="legend-labels"><span>Menos registros</span><span>Mais registros</span></div></div>`;}
 if(state.showCars&&selectedCode){const counts={};carLayer?.eachLayer(l=>{const status=l.feature.properties.status;counts[status]=(counts[status]||0)+1;});html+='<strong>Perímetros CAR · situação cadastral</strong>';html+=carLayer?Object.entries(statusInfo).map(([key,spec])=>legendLine(spec.name,mapPalette.cars[key].color,counts[key]||0,`stroke-dasharray="${esc(mapPalette.cars[key].dashArray||'')}"`)).join(''):'<p>Carregando perímetros…</p>';if(selectedProperty)html+=legendLine('CAR selecionado',mapPalette.carSelection.color,1);}
 if(typeof environmentalLegend==='function')html+=environmentalLegend();
 target.innerHTML=(html||'<p>Nenhuma camada de dados ativa.</p>')+'<p class="legend-note">Contagens da seleção municipal e dos filtros. Feições que cruzam municípios podem se repetir. Interseção não comprova infração.</p>';
}
function setCarVisibility(){
 for(const layer of [carLayer,propertyLayer])if(layer)state.showCars?layer.addTo(map):map.removeLayer(layer);
 renderMapLegend();
}
function createMapPanes(){
 for(const [name,z] of [['environmental-event',410],['environmental-outline',420],['environmental-point',430],['car-selection',450]]){
  const pane=map.createPane(name);
  pane.style.zIndex=z;
  pane.style.pointerEvents='none';
 }
}
function installLegend(){
 const legend=$('.map-legend'),mobile=matchMedia('(max-width:700px)');
 legend.open=false;
 mobile.addEventListener('change',event=>{if(event.matches)legend.open=false;});
}
function mapPage(){
 document.body.classList.add('map-page');
 $('#app').innerHTML=header()+`<main><section class="page-intro"><div class="breadcrumbs"><a href="index.html">Início</a>${icon('chevron')}<span>Mapa interativo</span></div><div class="page-title-row"><div><h1>Um território. Muitas perspectivas.</h1><p>Explore o Amazonas e os dados públicos de seus imóveis rurais.</p></div><button class="btn" id="export-map">${icon('download')} Exportar dados</button></div></section><div class="map-toolbar"><label class="search-input">${icon('search')}<input id="map-search" placeholder="Busque um município ou número do CAR" aria-label="Buscar município ou CAR" list="municipality-names"></label><datalist id="municipality-names">${catalog.municipalities.map(m=>`<option value="${esc(m.name)}"></option>`).join('')}</datalist><select id="municipality-select" aria-label="Município">${municipalityOptions('Todo o Amazonas')}</select><select id="map-metric" aria-label="Indicador do mapa"><option value="cadastros">Cadastros do CAR</option><option value="carbono">Carbono estimado</option><option value="degradacao">Degradação florestal</option><option value="fogo">Ocorrência de fogo</option></select><span class="toolbar-note">${icon('clock')} Referência: 05/11/2026</span></div><div class="map-layout"><aside class="layer-panel" aria-label="Camadas do mapa"><div class="panel-heading">CAMADAS ${icon('layers')}</div><div class="layer-group"><div class="panel-heading">BASE TERRITORIAL</div><label class="layer-item"><input type="checkbox" id="layer-counties" checked><span>Limites municipais</span><i class="layer-swatch"></i></label><label class="layer-item"><input type="checkbox" id="color-counties"><span>Colorir por registros CAR</span></label><label class="layer-item"><input type="checkbox" id="layer-cars" checked><span>Imóveis do CAR</span><i class="layer-swatch car"></i></label><div class="focos-layer"><label class="layer-item"><input type="checkbox" id="layer-focos-brasil"><span>Focos de calor - Brasil (INPE, satélite de referência)</span><i class="layer-swatch focos-swatch"></i></label><div id="focos-controls" hidden><label for="focos-period">Período<select id="focos-period"><option value="latest">Últimos 12 meses fechados</option><option value="year">Ano</option><option value="month">Mês</option></select></label><label id="focos-year-label" for="focos-year">Ano dos focos<select id="focos-year"></select></label><label id="focos-month-label" for="focos-month" hidden>Mês<select id="focos-month"></select></label><button class="btn btn-small" id="focos-fit" type="button">Brasil inteiro</button><div id="focos-class-legend" aria-label="Classes de focos por município"></div></div><p id="focos-status" role="status" hidden></p></div></div><div class="layer-group"><div class="panel-heading">ANÁLISE AMBIENTAL</div>${[['APP e Reserva Legal','app'],['Degradação florestal','degradacao'],['Estoque de carbono','carbono']].map(([t,k])=>`<label class="layer-item unavailable"><input type="checkbox" data-pending="${k}"><span>${t}</span><small class="pending-label">A integrar</small></label>`).join('')}</div><div class="layer-info">${icon('info')} Selecione um município para carregar seus perímetros do CAR.</div><div class="panel-heading base-heading">MAPA BASE</div><div class="base-toggle"><button data-base="satellite" class="active">Satélite</button><button data-base="terrain">Ruas</button></div></aside><div class="map-canvas-wrap satellite"><div id="main-map" class="main-map" role="region" aria-label="Mapa interativo do Amazonas"></div><div class="map-top-label"><span class="dot"></span><span id="map-top-text">Amazonas · 62 municípios</span></div><button class="map-help" id="fit-state" aria-label="Enquadrar todo o Amazonas">${icon('focus')}</button><details class="map-legend"><summary>Legenda do mapa</summary><div id="map-legend-content"></div></details><div class="basemap-note" id="basemap-note" role="status"><span id="basemap-status">Esri · Data da imagem desconhecida. Acima do zoom 16, imagem ampliada.</span><button id="retry-imagery" hidden>Tentar novamente</button></div><div id="map-loading" class="map-selection-loading" hidden>Carregando perímetros…</div></div><aside class="territory-panel" id="territory-panel" aria-live="polite"></aside></div></main>`+footer();
 map=L.map('main-map',{zoomControl:false,preferCanvas:true,zoomSnap:.25});L.control.zoom({position:'bottomright'}).addTo(map);
 imagery=satelliteLayer().addTo(map);
 installImageryStatus();
 createMapPanes();
 installLegend();
 terrain=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19});
 countyLayer=L.geoJSON(municipalitiesGeo,{bubblingMouseEvents:false,style:countyStyle,onEachFeature:(f,layer)=>{const m=muni(f.properties.code);layer.bindTooltip(`<strong>${esc(m.name)}</strong><br>${fmt(m.count)} registros do CAR`);layer.on({click:()=>selectMunicipality(m.code),mouseover:()=>layer.setStyle(countyStyle(f,true)),mouseout:()=>layer.setStyle(countyStyle(f))});}}).addTo(map);
 map.fitBounds(countyLayer.getBounds(),{padding:[20,20]});
 $('#color-counties').addEventListener('change',e=>{state.colorCounties=e.target.checked;countyLayer.setStyle(countyStyle);renderMapLegend();});
 $('#municipality-select').addEventListener('change',e=>selectMunicipality(e.target.value));
 $('#map-metric').addEventListener('change',e=>{if(e.target.value!=='cadastros'){toast('Esta camada ainda não tem dados integrados. Veja a cobertura e as fontes no painel de dados.');e.target.value='cadastros';}});
 $$('#layer-counties,#layer-cars').forEach(el=>el.addEventListener('change',()=>{state.showCounties=$('#layer-counties').checked;state.showCars=$('#layer-cars').checked;state.showCounties?countyLayer.addTo(map):map.removeLayer(countyLayer);setCarVisibility();}));
 $$('[data-pending]').forEach(el=>el.addEventListener('change',()=>{el.checked=false;toast('Integração pendente. Nenhum resultado ambiental foi calculado para esta camada.');}));
 $$('[data-base]').forEach(el=>el.addEventListener('click',()=>{state.base=el.dataset.base;map.removeLayer(imagery);map.removeLayer(terrain);(state.base==='satellite'?imagery:terrain).addTo(map);$('.map-canvas-wrap').classList.toggle('satellite',state.base==='satellite');$$('[data-base]').forEach(b=>b.classList.toggle('active',b===el));updateImageryStatus();}));
 $('#fit-state').addEventListener('click',()=>selectMunicipality(''));
 $('#export-map').addEventListener('click',exportCurrent);
 renderTerritory();renderMapLegend();initializeMapTools().catch(error=>toast(error.message));
}
function statusesHTML(statuses){return Object.entries(statusInfo).map(([s,c])=>`<div class="status-row"><span class="dot" style="background:${c.color}"></span>${c.plural}<b>${fmt(statuses[s]||0)}</b></div>`).join('');}
function trackHTML(statuses,total){return `<div class="mini-track">${Object.entries(statusInfo).map(([s,c])=>`<span style="width:${(statuses[s]||0)/total*100}%;background:${c.color}"></span>`).join('')}</div>`;}
function renderTerritory(){if(typeof nationalFocos!=='undefined'&&nationalFocos?.foreignPanel())return;const m=muni(selectedCode),statuses=getStatuses(),total=getCount();
 $('#territory-panel').innerHTML=`<div class="territory-top"><span class="state-code">${m?'MUNICÍPIO / AM':'ESTADO / BRASIL'}</span><span class="pill grey">${m?'IBGE '+m.code:'REGIÃO NORTE'}</span></div><h2>${esc(getName())}</h2><p class="territory-sub">${m?'Amazonas · Brasil':'Um olhar sobre o território amazônico'}</p>${selectedProperty?`<div class="selected-property"><strong>Imóvel selecionado</strong><p class="property-code">${esc(selectedProperty.code)}</p>${statusPill(selectedProperty.status)}<p style="font-size:10px;margin:10px 0 0">${fmt(selectedProperty.area,2)} ha declarados</p><button class="btn btn-small" id="property-to-data" style="margin-top:12px;width:100%">Analisar cadastro ${icon('arrow')}</button></div>`:''}<div class="territory-stats"><div><strong>${fmt(total)}</strong><label>Registros do CAR</label></div><div><strong>${m?'1':'62'}</strong><label>${m?'Município selecionado':'Municípios'}</label></div><div><strong>${fmt(m?m.area_km2:catalog.total_area_km2,0)}</strong><label>Área territorial · km²</label></div><div><strong>${fmt((statuses.AT||0)/total*100,1)}%</strong><label>Cadastros ativos</label></div></div><div class="status-list"><div class="panel-heading" style="margin-bottom:10px">SITUAÇÃO CADASTRAL</div>${trackHTML(statuses,total)}${statusesHTML(statuses)}</div><p class="panel-note">${icon('info')} Ativo é uma situação cadastral. Não comprova, por si só, a regularidade ambiental do imóvel.<br><br>Fonte: SICAR · Extração de 05/11/2026</p><a class="btn btn-primary" href="dados.html${selectedCode?'?municipio='+selectedCode:''}">Consultar ${m?'os cadastros':'a base de dados'} ${icon('arrow')}</a>`;
 if(typeof nationalFocos!=='undefined'&&nationalFocos){$('#territory-panel').insertAdjacentHTML('beforeend','<section id="focos-municipality" hidden></section>');nationalFocos.renderSelection();}
 if(m)$('#territory-panel').insertAdjacentHTML('beforeend',`<a class="btn btn-small attention-ranking-link" href="dados.html?municipio=${m.code}&aba=atencao">Imóveis que pedem atenção</a>`);
 if(selectedProperty){const record=selectedProperty;$('.selected-property').insertAdjacentHTML('beforeend','<section id="car-attention" aria-live="polite"></section>');AngelimAttention.renderDetail($('#car-attention'),record.code,municipalityForCar(record.code),()=>selectedProperty?.code===record.code);}
 if($('#property-to-data'))$('#property-to-data').onclick=()=>location.href=`dados.html?car=${encodeURIComponent(selectedProperty.code)}`;
}
function updateURL(car='',options={}){if(PAGE==='map'&&typeof writeMapURL==='function'){writeMapURL(car,options);return;}const query=new URLSearchParams();if(selectedCode)query.set('municipio',selectedCode);if(car)query.set('car',car);else if(PAGE==='data'&&currentTab==='atencao')query.set('aba','atencao');history.replaceState(null,'',location.pathname+(query.size?'?'+query:''));}
async function selectMunicipality(code,carCode='',options={}){
 if(code&&!muni(code)){toast('Município não encontrado na base do Amazonas.');return;}
 if(matchMedia('(max-width:700px)').matches)$('.map-legend').open=false;
 selectedCode=code;selectedProperty=null;if(typeof nationalFocos!=='undefined')nationalFocos?.select(code);const token=++displayToken;
 $('#municipality-select').value=code;
 if(carLayer){map.removeLayer(carLayer);carLayer=null;}if(propertyLayer){map.removeLayer(propertyLayer);propertyLayer=null;}
 countyLayer.setStyle(countyStyle);renderTerritory();renderMapLegend();updateURL(carCode,options);
 if(!code){if(options.fit!==false){if(typeof nationalFocos!=='undefined'&&nationalFocos?.enabled)nationalFocos.fit();else map.fitBounds(countyLayer.getBounds(),{padding:[20,20]});}$('#map-top-text').textContent='Amazonas · 62 municípios';$('#map-loading').hidden=true;return;}
 const m=muni(code);if(options.fit!==false)map.fitBounds([[m.bounds[1],m.bounds[0]],[m.bounds[3],m.bounds[2]]],{padding:[26,26]});$('#map-top-text').textContent=`${m.name} · ${fmt(m.count)} registros`;
 $('#map-loading').hidden=false;
 try{const [geo,records]=await Promise.all([fetchJSON(`data/mapa/${code}.geojson`),recordsFor(code)]);if(token!==displayToken)return;
  const lookup=new Map(records.map(r=>[r.code,r]));
  carLayer=L.geoJSON(geo,{bubblingMouseEvents:false,style:f=>HibamaVisual.carStyle(mapPalette,f.properties.status),onEachFeature:(f,l)=>{l.bindTooltip(`${esc(f.properties.code.slice(0,10))}…<br>${esc(statusInfo[f.properties.status]?.name||f.properties.status)}`);l.on({click:()=>chooseMapProperty(lookup.get(f.properties.code)),mouseover:()=>l.setStyle(HibamaVisual.carStyle(mapPalette,f.properties.status,true)),mouseout:()=>l.setStyle(HibamaVisual.carStyle(mapPalette,f.properties.status))});}});
  if(state.showCars)carLayer.addTo(map);renderMapLegend();
  if(carCode){const r=lookup.get(carCode);if(r)await chooseMapProperty(r,options);else {toast('Esse CAR não foi encontrado na extração de 05/11/2026. Seleção restaurada para o padrão.');if(typeof writeMapURL==='function')writeMapURL('',{replace:true});}}
 }catch(e){if(token===displayToken)toast(e.message);}finally{if(token===displayToken)$('#map-loading').hidden=true;}
}
async function chooseMapProperty(record,options={}){if(!record)return;selectedProperty=record;renderTerritory();renderMapLegend();updateURL(record.code,options);if(propertyLayer)map.removeLayer(propertyLayer);const code=selectedCode;
 try{const geos=await fetchJSON(`data/geometrias/${code}.json`);if(selectedProperty?.code!==record.code||selectedCode!==code)return;propertyLayer=L.geoJSON({type:'Feature',properties:{},geometry:geos[record.code]},{pane:'car-selection',style:{color:mapPalette.carSelection.color,weight:3,fillColor:mapPalette.carSelection.color,fillOpacity:.1},interactive:false});if(state.showCars)propertyLayer.addTo(map);map.fitBounds(propertyLayer.getBounds(),{padding:[45,45],maxZoom:16});}catch(e){toast(e.message);}
}
function searchTerritory(value){const v=value.trim();if(!v)return;const car=v.toUpperCase().replace(/\s/g,'');if(/^AM-\d{7}-[A-F0-9]{32}$/.test(car)){selectMunicipality(municipalityForCar(car),car);return;}if(typeof searchLocalTerritory==='function'){searchLocalTerritory(v);return;}const exact=catalog.municipalities.find(m=>norm(m.name)===norm(v));const options=catalog.municipalities.filter(m=>norm(m.name).includes(norm(v)));if(exact||options.length===1)selectMunicipality((exact||options[0]).code);else toast(options.length?'Escolha o nome completo do município na lista.':'Município ou número do CAR não encontrado.');}
function dataPage(){
 $('#app').innerHTML=header()+`<main><section class="page-intro"><div class="breadcrumbs"><a href="index.html">Início</a>${icon('chevron')}<span>Dados & CAR</span></div><div class="page-title-row"><div><h1>Dados que fundamentam a análise.</h1><p>Consulte cadastros, verifique a origem e organize suas evidências.</p></div><button class="btn" id="export-data">${icon('download')} Exportar dados</button></div></section><div class="data-layout"><div class="metric-grid" id="data-metrics"></div><div class="data-main"><section class="data-card"><div class="tabs" role="tablist" aria-label="Dados e fontes"><button role="tab" data-tab="cadastros" class="active" aria-selected="true">Cadastros do CAR</button><button role="tab" data-tab="atencao" aria-selected="false">Imóveis que pedem atenção</button><button role="tab" data-tab="fontes" aria-selected="false">Cobertura e fontes</button><button role="tab" data-tab="imovel" aria-selected="false">Dossiê do imóvel</button></div><div class="tab-content" id="tab-content"></div></section><aside class="data-sidebar" id="data-sidebar"></aside></div></div></main>`+footer();
 $$('[data-tab]').forEach(b=>b.addEventListener('click',()=>switchTab(b.dataset.tab)));
 $('#export-data').addEventListener('click',exportCurrent);
 renderMetrics();renderDataSidebar();
 if(params.get('aba')==='fontes')switchTab('fontes');else if(params.get('aba')==='atencao')switchTab('atencao');else renderCadastros();
 if(params.get('car'))loadDataCar(params.get('car'));
}
function renderMetrics(){const sts=getStatuses(),count=getCount();$('#data-metrics').innerHTML=`<article class="metric-card highlight"><div>Registros públicos ${icon('database')}</div><strong>${fmt(count)}</strong><small>${selectedCode?esc(getName()):'Todo o Amazonas'} · SICAR</small></article><article class="metric-card"><div>Cadastros ativos ${icon('check')}</div><strong>${fmt(sts.AT||0)}</strong><small>${fmt((sts.AT||0)/count*100,1)}% dos registros selecionados</small></article><article class="metric-card"><div>Municípios na seleção ${icon('map')}</div><strong>${selectedCode?'01':'62'}</strong><small>${selectedCode?'Recorte municipal':'Cobertura estadual completa'}</small></article><article class="metric-card"><div>Referência da base ${icon('clock')}</div><strong style="font-size:26px">05 nov. <span style="color:#9aa68a">2026</span></strong><small>Extração conferida · atualização manual</small></article>`;}
function switchTab(tab){currentTab=tab;if(PAGE==='data'&&tab!=='atencao'&&new URLSearchParams(location.search).get('aba')==='atencao')updateURL(tab==='imovel'?selectedProperty?.code||'':'');$$('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===tab);b.setAttribute('aria-selected',String(b.dataset.tab===tab));});if(tab==='fontes')renderSources();else if(tab==='atencao'){updateURL();renderAttentionList();}else if(tab==='imovel')renderPropertyDetail();else renderCadastros();}
async function renderCadastros(){
 $('#tab-content').innerHTML=`<div class="data-filters"><label class="search-input">${icon('search')}<input id="data-search" placeholder="Busque município ou cole o número completo do CAR" aria-label="Buscar cadastro ou município" value="${esc(state.query)}"></label><select id="data-municipality" aria-label="Filtrar município">${municipalityOptions()}</select><select id="data-status" aria-label="Filtrar situação cadastral"><option value="">Todas as situações</option>${Object.entries(statusInfo).map(([s,c])=>`<option value="${s}" ${state.status===s?'selected':''}>${c.plural}</option>`).join('')}</select></div><div id="records-table"><div class="empty-state">Carregando registros…</div></div><div class="source-footnote">${icon('info')} Dados declarados no CAR. Áreas de cadastros podem se sobrepor e não representam cobertura territorial quando somadas.</div>`;
 $('#data-municipality').onchange=async e=>{selectedCode=e.target.value;selectedProperty=null;tablePage=0;state.query='';$('#data-search').value='';updateURL();renderMetrics();renderDataSidebar();await renderTable();};
 $('#data-status').onchange=e=>{state.status=e.target.value;tablePage=0;renderTable();};
 const search=$('#data-search');search.oninput=e=>{state.query=e.target.value;tablePage=0;clearTimeout(search.timer);search.timer=setTimeout(()=>renderTable(),180);};search.onkeydown=e=>{if(e.key==='Enter')renderTable();};await renderTable();
}
async function renderTable(){const target=$('#records-table');if(!target)return;const query=state.query.trim();
 const car=query.toUpperCase().replace(/\s/g,'');if(/^AM-\d{7}-[A-F0-9]{32}$/.test(car)){await loadDataCar(car);return;}
 try{
 if(!selectedCode){let ms=catalog.municipalities.filter(m=>norm(m.name).includes(norm(query))||m.code.includes(query));if(state.status)ms=ms.filter(m=>(m.statuses[state.status]||0)>0);const rows=ms.slice(tablePage*12,(tablePage+1)*12);
 target.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Município / AM</th><th>Registros do CAR</th><th>Ativos</th><th>Área · km²</th><th></th></tr></thead><tbody>${rows.map(m=>`<tr><td><strong>${esc(m.name)}</strong><br><span style="font-size:8px;color:#a1aa95">IBGE ${m.code}</span></td><td>${fmt(state.status?m.statuses[state.status]||0:m.count)}</td><td>${fmt(m.statuses.AT||0)}</td><td>${fmt(m.area_km2,0)}</td><td><button class="table-action" data-open-muni="${m.code}" aria-label="Ver cadastros de ${esc(m.name)}">${icon('arrow')}</button></td></tr>`).join('')||'<tr><td colspan="5">Nenhum município encontrado.</td></tr>'}</tbody></table></div>${pagination(ms.length,12,'municípios')}`;
 $$('[data-open-muni]').forEach(b=>b.onclick=()=>{selectedCode=b.dataset.openMuni;state.query='';tablePage=0;updateURL();renderMetrics();renderDataSidebar();renderCadastros();});
 }else{const current=selectedCode;const records=await recordsFor(current);if(current!==selectedCode||currentTab!=='cadastros')return;const rs=records.filter(r=>(!state.status||r.status===state.status)&&(!query||norm(r.code+' '+r.condition+' '+typeNames[r.type]).includes(norm(query))));const rows=rs.slice(tablePage*12,(tablePage+1)*12);
 target.innerHTML=`<div style="font-size:10px;color:#7e8e70;margin:0 0 14px">${esc(getName())} <span style="color:#acb39e">/ ${fmt(rs.length)} cadastros encontrados</span></div><div class="table-wrap"><table><thead><tr><th>Registro do CAR</th><th>Situação</th><th>Área · ha</th><th>Atualização</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td title="${esc(r.code)}"><strong class="small-code">${r.code.slice(0,10)}…${r.code.slice(-7)}</strong><br><span style="font-size:8px;color:#9aa58b">${esc(typeNames[r.type]||r.type)}</span></td><td>${statusPill(r.status)}</td><td>${fmt(r.area,2)}</td><td>${date(r.updated)}</td><td><button class="table-action" data-open-car="${r.code}" aria-label="Ver dossiê do CAR ${r.code}">${icon('arrow')}</button></td></tr>`).join('')||'<tr><td colspan="5">Nenhum cadastro corresponde aos filtros.</td></tr>'}</tbody></table></div>${pagination(rs.length,12,'cadastros')}`;
 $$('[data-open-car]').forEach(b=>b.onclick=()=>{selectedProperty=records.find(r=>r.code===b.dataset.openCar);updateURL(selectedProperty.code);renderDataSidebar();switchTab('imovel');});}
 const previous=$('#previous-page'),next=$('#next-page');if(previous)previous.onclick=()=>{tablePage--;renderTable();};if(next)next.onclick=()=>{tablePage++;renderTable();};
 }catch(e){target.innerHTML=`<div class="empty-state">${esc(e.message)}<br><button class="btn btn-small" id="retry-records">Tentar novamente</button></div>`;$('#retry-records').onclick=renderTable;}
}
function pagination(total,size,label){return `<div class="pagination"><span>${total?fmt(tablePage*size+1):0}–${fmt(Math.min((tablePage+1)*size,total))} de ${fmt(total)} ${label}</span><div class="pagination-buttons"><button id="previous-page" ${tablePage===0?'disabled':''} aria-label="Página anterior">‹</button><button id="next-page" ${(tablePage+1)*size>=total?'disabled':''} aria-label="Próxima página">›</button></div></div>`;}
function renderDataSidebar(){const sts=getStatuses(),total=getCount();let degrees=0;const stops=Object.entries(statusInfo).map(([s,c])=>{const start=degrees;degrees+=(sts[s]||0)/total*360;return `${c.color} ${start}deg ${degrees}deg`;}).join(',');
 $('#data-sidebar').innerHTML=`<div class="side-card"><h3>Um retrato dos cadastros.</h3><p>${esc(getName())} · Situação publicada pelo SICAR</p><div class="donut-wrap"><div class="donut" style="background:conic-gradient(${stops})"><div class="donut-center"><strong>${fmt((sts.AT||0)/total*100,1)}%</strong><small>cadastros ativos</small></div></div></div><div class="status-list">${statusesHTML(sts)}</div></div><div class="side-card"><h3>Cobertura da análise</h3><p>Acompanhe quais evidências já estão disponíveis.</p><div class="source-check">${icon('check')}Perímetros e atributos do CAR</div><div class="source-check">${icon('check')}Limites municipais do IBGE</div><div class="source-check"><span class="pending">${icon('clock')}</span>Degradação e fogo · a integrar</div><div class="source-check"><span class="pending">${icon('clock')}</span>Estimativas de carbono · a integrar</div><button class="btn btn-small" id="view-sources" style="width:100%;margin-top:10px">Ver fontes e limitações ${icon('arrow')}</button></div><div class="notice">${icon('shield')}<span>A situação cadastral não é um atestado de regularidade ambiental. Os achados exigem análise técnica e documental.</span></div>`;
 $('#view-sources').onclick=()=>switchTab('fontes');
}
function renderSources(){$('#tab-content').innerHTML=`<div style="margin-bottom:20px"><h2 style="font-size:18px;font-weight:450;margin-bottom:8px">A origem faz parte da evidência.</h2><p style="font-size:11px;color:#8b967d;line-height:1.8">Duas bases integradas nesta versão. Resultados ambientais só serão apresentados depois de integrar e validar as respectivas fontes.</p></div><div class="source-grid">${catalog.sources.map(s=>`<article class="source-item"><span class="source-symbol">${icon(s.status==='integrado'?'database':'layers')}</span><div><h3>${esc(s.name)}</h3><p>${esc(s.scope)}${s.date?' · '+s.date:''}</p><a href="${s.url}" target="_blank" rel="noopener noreferrer">Consultar fonte oficial ${icon('external')}</a></div><span class="pill ${s.status==='integrado'?'':'grey'}">${s.status==='integrado'?'Integrado':'A integrar'}</span></article>`).join('')}</div><p class="source-footnote">Referência cadastral: 05/11/2026. A extração contém ${fmt(catalog.total)} códigos únicos, com registros em todos os 62 municípios. A base é uma cópia datada, sem atualização automática. Polígonos do mapa são simplificados para exibição; a exportação de um imóvel preserva sua geometria de origem. Não foi executada validação topológica.<br><br>As imagens do mapa base são fornecidas pela Esri e não representam, necessariamente, a data da extração do CAR. Não devem ser usadas como comparação temporal sem verificar sua data de aquisição.<br><br><a href="data/proveniencia.json" download>Baixar proveniência e conferência da extração</a></p>`;}
async function loadDataCar(code){const municipality=municipalityForCar(code);if(!muni(municipality)){toast('Esse CAR não pertence a um município reconhecido do Amazonas.');return;}try{const records=await recordsFor(municipality);const r=records.find(x=>x.code===code);if(!r){toast('CAR não encontrado na extração de 05/11/2026.');return;}selectedCode=municipality;selectedProperty=r;state.query='';tablePage=0;updateURL(code);renderMetrics();renderDataSidebar();switchTab('imovel');}catch(e){toast(e.message);}}
function renderPropertyDetail(){const r=selectedProperty;if(!r){$('#tab-content').innerHTML=`<div class="empty-state">${icon('file')}<h3>Comece por um imóvel.</h3>Selecione um município na aba Cadastros do CAR<br>e abra o registro que deseja investigar.<br><button id="back-records" class="btn btn-primary" style="margin-top:20px">Consultar cadastros ${icon('arrow')}</button></div>`;$('#back-records').onclick=()=>switchTab('cadastros');return;}
 const fields=[['Município',getName()+' / AM'],['Tipo de cadastro',typeNames[r.type]||r.type],['Área declarada',fmt(r.area,4)+' ha'],['Módulos fiscais',fmt(r.modules,4)],['Inscrição',date(r.created)],['Atualização do registro',date(r.updated)],['Condição de análise',r.condition]];
 $('#tab-content').innerHTML=`<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><h2 style="font-size:20px;font-weight:450;margin:0">Dossiê cadastral do imóvel</h2>${statusPill(r.status)}</div><p class="property-code" style="font-size:11px;margin-bottom:25px">${esc(r.code)}</p><div class="detail-grid">${fields.map(([k,v])=>`<div class="detail-field" ${k==='Condição de análise'?'style="grid-column:1/-1"':''}><label>${k}</label><strong>${esc(v)}</strong></div>`).join('')}</div><section id="car-attention" aria-live="polite"></section><div style="border-top:1px solid var(--line);margin-top:25px;padding-top:23px"><label for="property-notes" style="font-size:11px;font-weight:550">Observações do analista</label><textarea id="property-notes" class="property-notes" placeholder="Registre documentos a consultar, perguntas e observações. Salvo apenas neste navegador."></textarea><div style="font-size:9px;color:#9aa58b">Anotações ficam neste navegador e serão incluídas no dossiê exportado.</div></div><div class="detail-actions"><button class="btn btn-primary" id="generate-report">${icon('file')} Gerar dossiê</button><a class="btn" href="mapa.html?car=${encodeURIComponent(r.code)}">${icon('map')} Ver no mapa</a><button class="btn" id="download-geometry">${icon('download')} Geometria (GeoJSON p/ QGIS)</button></div><div class="notice" style="margin-top:24px">${icon('info')}<span>Este dossiê reúne dados cadastrais e priorização por regras. A ausência de um resultado não indica ausência de ocorrência.</span></div><div class="source-footnote">Fonte: SICAR · Base extraída em 05/11/2026.<br><a href="https://consulta.car.gov.br/" target="_blank" rel="noopener noreferrer">Consultar o demonstrativo no portal oficial do CAR</a> usando o número completo acima.</div>`;
 const notes=$('#property-notes');try{notes.value=localStorage.getItem('hibama-note:'+r.code)||'';}catch{}
 notes.oninput=()=>{try{localStorage.setItem('hibama-note:'+r.code,notes.value);}catch{toast('Não foi possível salvar a anotação neste navegador.');}};
 $('#generate-report').onclick=()=>openReport(r,notes.value);
 $('#download-geometry').onclick=()=>downloadProperty(r);
 AngelimAttention.renderDetail($('#car-attention'),r.code,municipalityForCar(r.code),()=>currentTab==='imovel'&&selectedProperty?.code===r.code);
 renderFocusSample(r);
}
function downloadBlob(data,name,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
async function downloadProperty(r){const code=municipalityForCar(r.code);try{const geos=await fetchJSON(`data/geometrias/${code}.json`);const feature={type:'Feature',geometry:geos[r.code],properties:{...r,municipio:muni(code).name,fonte:'SICAR WFS público',referencia:'2026-11-05',validacao_topologica:'não executada'}};downloadBlob(JSON.stringify(feature,null,2),r.code+'.geojson','application/geo+json');toast('Geometria de origem exportada com os atributos cadastrais.');}catch(e){toast(e.message);}}
async function exportCurrent(){try{if(selectedProperty){let n='';try{n=localStorage.getItem('hibama-note:'+selectedProperty.code)||'';}catch{}await openReport(selectedProperty,n);return;}if(selectedCode){await openMunicipalityReport(selectedCode);}else{toast('Selecione um município para gerar o relatório em PDF.');}}catch(e){toast(e.message);}}
function reportBody(r,notes,ctx){const code=municipalityForCar(r.code);return `<div class="report-body">${brand()}<div class="eyebrow" style="margin-top:30px">DOSSIÊ CADASTRAL · AMAZONAS</div><h1>Uma base para<br>aprofundar a análise.</h1><p>Relatório preliminar de informações públicas do CAR.<br>Referência da extração: 05/11/2026 · Emitido em ${date(new Date().toISOString())}</p><h2>01. Identificação e informações declaradas</h2><table><tbody>${[['Código do CAR',r.code],['Município',muni(code).name+' / AM'],['Situação cadastral',statusInfo[r.status]?.name||r.status],['Condição publicada',r.condition],['Tipo',typeNames[r.type]||r.type],['Área declarada',fmt(r.area,4)+' ha'],['Módulos fiscais',fmt(r.modules,4)],['Data de inscrição',date(r.created)],['Atualização do registro',date(r.updated)]].map(([k,v])=>`<tr><td>${k}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table><h2>02. Evidências disponíveis</h2><p>Perímetro declarado e atributos cadastrais publicados pelo serviço WFS do SICAR. Contexto municipal baseado na malha do IBGE de 2025. Os dados foram extraídos em 05/11/2026; não há consulta em tempo real neste dossiê.</p>${reportEnvironment(ctx)}<h2>04. Observações do analista</h2><p style="white-space:pre-wrap">${esc(notes||'Nenhuma observação registrada.')}</p><h2>05. Limitações e rastreabilidade</h2><p>O CAR é declaratório. A situação Ativo não comprova regularidade ambiental. Cadastros podem se sobrepor; suas áreas não devem ser somadas como cobertura territorial. Não foi executada validação topológica. Imagens do mapa base não constituem evidência temporal sem data de aquisição verificada. Este documento não é um laudo conclusivo nem uma decisão do órgão ambiental.</p><p>Fonte cadastral: <a href="https://consulta.car.gov.br/">consulta.car.gov.br</a><br>Serviço geográfico: geoserver.car.gov.br/geoserver/sicar/wfs<br>Limites municipais: IBGE · Malha municipal 2025</p><div class="report-hash">SHA-256 do arquivo consolidado da extração:<br>${catalog.source_sha256}</div></div>`;}
function showReport(r,notes,ctx){const dialog=$('#report-dialog');dialog.innerHTML=`<div class="report-toolbar"><strong>Prévia do dossiê cadastral</strong><div class="report-actions"><button class="btn btn-primary btn-small" id="report-print">${icon('print')} Exportar PDF</button><button class="report-close" id="report-close" aria-label="Fechar dossiê">${icon('close')}</button></div></div>${reportBody(r,notes,ctx)}`;dialog.showModal();$('#report-close').onclick=()=>dialog.close();$('#report-print').onclick=()=>window.print();if($('#report-download'))$('#report-download').onclick=()=>{const html=`<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Dossiê CAR ${esc(r.code)}</title><style>body{max-width:850px;margin:40px auto;padding:0 25px;font:14px/1.8 Arial,sans-serif;color:#294d3a}h1{font:42px Georgia,serif}h2{font-size:16px;margin-top:30px}table{width:100%;border-collapse:collapse}td{padding:9px;border-bottom:1px solid #ddd;word-break:break-word}a{color:#294d3a}.brand{font:bold 28px Arial;text-decoration:none}.brand-mark{display:none}.report-hash{font-size:10px;word-break:break-all}.eyebrow{font-size:11px;letter-spacing:2px}</style></head><body>${reportBody(r,notes,ctx)}</body></html>`;downloadBlob(html,`Curupira_Dossie_${r.code}.html`,'text/html;charset=utf-8');};}
async function init(){try{if(PAGE==='map'||PAGE==='home'){let palette;try{palette=await fetchJSON('data/ambiental/paleta.json?v=etapa2a-3');}catch{throw new Error('Paleta visual ausente ou ilegível. Restaure data/ambiental/paleta.json e recarregue.');}mapPalette=HibamaVisual.validatePalette(palette);}[catalog,municipalitiesGeo,carMunicipalityIndex]=await Promise.all([fetchJSON('data/catalogo.json?v=etapa5a-2'),fetchJSON('data/municipios.geojson'),fetchJSON('data/indice_car.json')]);if(params.get('car'))selectedCode=municipalityForCar(params.get('car'));if(selectedCode&&!muni(selectedCode))selectedCode='';if(PAGE==='home')home();else if(PAGE==='map')mapPage();else dataPage();}catch(e){$('#app').innerHTML=`<main class="empty-state" style="padding-top:20vh"><h1>Não foi possível abrir a base.</h1><p>${esc(e.message)}</p><button class="btn btn-primary" onclick="location.reload()">Recarregar</button></main>`;console.error(e);}}
init();

async function renderFocusSample(record){
 const label='Focos 29/10 a 04/11/2026, todos os satélites (amostra AM)';
 $('#tab-content').insertAdjacentHTML('beforeend',`<section id="car-focus-sample" class="side-card"><h3>${label}</h3><p role="status">Carregando cruzamento local da amostra…</p></section>`);
 try{const intersections=await fetchJSON(`data/ambiental/intersecoes/${municipalityForCar(record.code)}.json`);if(selectedProperty?.code!==record.code||currentTab!=='imovel')return;const target=$('#car-focus-sample p');if(target)target.textContent=fmt(intersections[record.code]?.focos?.count||0)+' detecções intersectam o perímetro na amostra. Interseção não comprova infração; esta contagem não é a série nacional de referência.';}
 catch{if(selectedProperty?.code===record.code&&$('#car-focus-sample p'))$('#car-focus-sample p').textContent='Sem dado: cruzamento local da amostra indisponível.';}
}

function renderAttentionList(){
 const municipality=selectedCode;
 AngelimAttention.renderList($('#tab-content'),{
  municipio:municipality,municipalities:catalog.municipalities,
  isCurrent:()=>currentTab==='atencao'&&selectedCode===municipality,
  onSelectMunicipality:code=>{selectedCode=code;selectedProperty=null;updateURL();renderMetrics();renderDataSidebar();renderAttentionList();},
  onOpen:async code=>{try{await recordsFor(municipality);if(currentTab==='atencao'&&selectedCode===municipality)await loadDataCar(code);}catch{if(currentTab==='atencao'&&selectedCode===municipality)toast('Não foi possível abrir o CAR. Tente novamente.');}}
 });
}

// Dossiê: busca o índice do CAR e o indicador de água do município antes de abrir.
// Se algum arquivo falhar, o dossiê abre mesmo assim, só sem essa parte.
const deterNames={DESMATAMENTO_CR:'Desmatamento (corte raso)',DESMATAMENTO_VEG:'Desmatamento com vegetação',CICATRIZ_DE_QUEIMADA:'Cicatriz de queimada',DEGRADACAO:'Degradação',MINERACAO:'Mineração',CS_DESORDENADO:'Corte seletivo desordenado',CS_GEOMETRICO:'Corte seletivo geométrico',CORTE_SELETIVO:'Corte seletivo'};
async function openReport(r,notes){
 const code=municipalityForCar(r.code),ctx={};
 const [att,water]=await Promise.allSettled([fetchJSON(`data/atencao/municipios/${code}.json`),fetchJSON('data/agua/indicador.json?v=1.0.0')]);
 if(att.status==='fulfilled'){ctx.car=att.value.by_car&&att.value.by_car[r.code];ctx.disclaimer=att.value.disclaimer;}
 if(water.status==='fulfilled')ctx.water=water.value.municipios&&water.value.municipios[code];
 showReport(r,notes,ctx);
}
function reportEnvironment(ctx){
 const pend='';
 if(!ctx||!ctx.car)return `<h2>03. Contexto ambiental da área do CAR</h2><p>Não foi possível carregar o cruzamento ambiental deste cadastro. Recarregue a página e gere o dossiê de novo.</p>${pend}`;
 const c=ctx.car,n=c.contagens||{},classes=Object.entries(c.classes_deter||{});
 const rows=[
  ['Índice de atenção',fmt(c.nota,1)+' / 100'+(c.travas&&c.travas.length?' · trava: '+c.travas.join(', '):'')],
  ['Sobreposição com Terra Indígena (FUNAI)',n.ti?n.ti+' área(s)':'Não encontrada'],
  ['Áreas embargadas (IPAAM/Ibama)',n.embargos?n.embargos+' registro(s)':'Não encontrado'],
  ['Desmatamento PRODES dentro do CAR',n.prodes?n.prodes+' polígono(s) · '+fmt(c.prodes_no_car_ha,2)+' ha ('+fmt(100*(c.fracao_prodes||0),1)+'% da área declarada)':'Não encontrado'],
  ['Alertas DETER',n.deter?n.deter+' alerta(s)'+(classes.length?': '+classes.map(([k,v])=>(deterNames[k]||k)+' '+v).join(', '):''):'Nenhum'],
  ['Processos minerários ANM',n.anm?n.anm+' processo(s)':'Nenhum'],
  ['Focos de calor INPE',n.focos?n.focos+' foco(s)':'Nenhum'],
  ['Pressão sobre a água no município',ctx.water?ctx.water.score+' / 100 ('+ctx.water.classe+') · estimativa por regras':'Indisponível']
 ];
 return `<h2>03. Contexto ambiental da área do CAR</h2><p>Cruzamento do perímetro declarado com bases públicas (FUNAI, IPAAM/Ibama, INPE PRODES/DETER/focos, ANM).</p><table><tbody>${rows.map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table><p>${esc(ctx.disclaimer||'Índice por regras sobre dados públicos. Não é laudo nem prova de infração.')} A pressão sobre a água é uma estimativa por regras; medição de turbidez por satélite em desenvolvimento.</p>${pend}`;
}

// Relatório do município (prévia + PDF). Usa os filtros que estiverem ligados na tela.
async function openMunicipalityReport(code){
 const m=muni(code),rs=await recordsFor(code),out=rs.filter(r=>!state.status||r.status===state.status);
 const [att,water,al]=await Promise.allSettled([fetchJSON(`data/atencao/municipios/${code}.json`),fetchJSON('data/agua/indicador.json?v=1.0.0'),fetchJSON('data/alertas/am-6meses.json?v=1.0.0')]);
 const ok=x=>x.status==='fulfilled'?x.value:null,A=ok(att),W=ok(water),AL=ok(al);
 const ef=(typeof environmentalFilters!=='undefined')?environmentalFilters:{};
 const row=(k,v)=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`,tabela=rows=>`<table><tbody>${rows.map(([k,v])=>row(k,v)).join('')}</tbody></table>`;
 // 01 filtros
 const filtros=[['Município',m.name+' / AM'],['Situação cadastral',state.status?(statusInfo[state.status]?.name||state.status):'Todas'],['Período (PRODES/DETER)',ef.start||ef.end?`${ef.start?date(ef.start+'T12:00'):'início'} a ${ef.end?date(ef.end+'T12:00'):'hoje'}`:'Todo o histórico'],['Classe DETER',ef.category||'Todas'],['Emitido em',date(new Date().toISOString())]];
 // 02 cadastros
 const porStatus={};out.forEach(r=>{porStatus[r.status]=(porStatus[r.status]||0)+1;});
 const area=out.reduce((a,r)=>a+(Number(r.area)||0),0);
 const cad=[['Imóveis no relatório',fmt(out.length)],['Área declarada somada',fmt(area,1)+' ha (cadastros podem se sobrepor)'],...Object.entries(porStatus).map(([k,v])=>[statusInfo[k]?.plural||k,fmt(v)])];
 // 03 alertas
 let alertas='<p>Alertas indisponíveis.</p>';
 if(AL){const g=(AL.municipios||{})[code];
  if(!g)alertas='<p>Nenhum alerta DETER nos últimos 6 meses.</p>';
  else{const pc={};AL.pontos.filter(p=>p[2]===code).forEach(p=>{pc[p[3]]=(pc[p[3]]||0)+1;});
   const nomes=typeof deterNames!=='undefined'?deterNames:{};
   alertas=tabela([['Total (últimos 6 meses)',fmt(g.total)+' alertas · '+fmt(g.ha)+' ha'],['Prioridade crítica',fmt(g.por_prioridade.critica)],['Prioridade alta',fmt(g.por_prioridade.alta)],['Prioridade média',fmt(g.por_prioridade.media)],['Prioridade baixa',fmt(g.por_prioridade.baixa)],...Object.entries(pc).sort((a,b)=>b[1]-a[1]).map(([k,v])=>[nomes[k]||k,fmt(v)])]);}}
 // 04 e 05 contexto por imóvel e ranking
 let contexto='<p>Cruzamento por imóvel indisponível.</p>',ranking='';
 if(A&&A.by_car){const cods=new Set(out.map(r=>r.code)),lista=Object.entries(A.by_car).filter(([c])=>cods.has(c));
  const conta=k=>lista.filter(([,v])=>(v.contagens||{})[k]>0).length;
  contexto=tabela([['Imóveis sobre Terra Indígena',fmt(conta('ti'))],['Imóveis com embargo',fmt(conta('embargos'))],['Imóveis com desmatamento PRODES',fmt(conta('prodes'))],['Imóveis com alerta DETER',fmt(conta('deter'))],['Imóveis com processo ANM',fmt(conta('anm'))],['Imóveis com foco de calor',fmt(conta('focos'))]]);
  const top=lista.filter(([,v])=>v.nota>0).sort((a,b)=>b[1].nota-a[1].nota).slice(0,20);
  ranking=top.length?`<table><thead><tr><td><b>Código CAR</b></td><td><b>Nota</b></td><td><b>Trava</b></td></tr></thead><tbody>${top.map(([c,v])=>`<tr><td>${esc(c)}</td><td>${esc(fmt(v.nota,1))}</td><td>${esc((v.travas||[]).join(', ')||'—')}</td></tr>`).join('')}</tbody></table>`:'<p>Nenhum imóvel com nota positiva.</p>';}
 const agua=W&&W.municipios&&W.municipios[code]?tabela([['Pressão sobre a água',W.municipios[code].score+' / 100 ('+W.municipios[code].classe+')'],['Base','Estimativa por regras (mineração e desmatamento recente). Medição de turbidez por satélite em desenvolvimento.']]):'<p>Indicador indisponível.</p>';
 const corpo=`<div class="report-body">${brand()}<div class="eyebrow" style="margin-top:30px">RELATÓRIO MUNICIPAL · AMAZÔNIA</div><h1>${esc(m.name)}</h1><p>Dados públicos consolidados do CAR e das bases ambientais.<br>Referência da extração: 05/11/2026</p><h2>01. Filtros aplicados</h2>${tabela(filtros)}<h2>02. Cadastros do CAR</h2>${tabela(cad)}<h2>03. Alertas DETER</h2>${alertas}<h2>04. Contexto ambiental dos imóveis</h2>${contexto}<h2>05. Imóveis com maior atenção (top 20)</h2>${ranking||'<p>Indisponível.</p>'}<h2>06. Água</h2>${agua}<h2>07. Limitações e fontes</h2><p>O CAR é declaratório. Sobreposição não comprova infração. O índice de atenção é por regras e não é laudo. Fontes: SICAR, IBGE, INPE (PRODES, DETER, focos; CC BY-SA 4.0), FUNAI, IPAAM/Ibama, ANM.</p><div class="report-hash">SHA-256 da extração cadastral:<br>${catalog.source_sha256}</div></div>`;
 // versão só com os alertas (lista completa do município)
 let soAlertas='<p>Alertas indisponíveis.</p>';
 if(AL){const nomes=typeof deterNames!=='undefined'?deterNames:{},pr={critica:'Crítica',alta:'Alta',media:'Média',baixa:'Baixa'};
  const lista=AL.pontos.filter(p=>p[2]===code).sort((a,b)=>a[4]<b[4]?1:-1);
  soAlertas=lista.length?`<table><thead><tr><td><b>Data</b></td><td><b>Tipo</b></td><td><b>Área (ha)</b></td><td><b>Prioridade</b></td><td><b>Lat, Lon</b></td></tr></thead><tbody>${lista.map(p=>`<tr><td>${esc(p[4].split('-').reverse().join('/'))}</td><td>${esc(nomes[p[3]]||p[3])}</td><td>${esc(fmt(p[5],2))}</td><td>${esc(pr[p[6]]||p[6])}</td><td>${esc(p[1].toFixed(4)+', '+p[0].toFixed(4))}</td></tr>`).join('')}</tbody></table>`:'<p>Nenhum alerta DETER nos últimos 6 meses.</p>';}
 const corpoAlertas=`<div class="report-body">${brand()}<div class="eyebrow" style="margin-top:30px">RELATÓRIO DE ALERTAS · AMAZÔNIA</div><h1>${esc(m.name)}</h1><p>Alertas DETER/INPE dos últimos 6 meses. Prioridade por regra (classe e idade do alerta).</p><h2>01. Resumo</h2>${alertas}<h2>02. Lista de alertas</h2>${soAlertas}<h2>03. Limitações e fontes</h2><p>Alerta é indício para análise, não prova de infração. Para saber se está dentro de um imóvel, compare com o perímetro do CAR no mapa. Fonte: INPE DETER (CC BY-SA 4.0).</p></div>`;
 const dialog=$('#report-dialog');
 dialog.innerHTML=`<div class="report-toolbar"><strong>Relatório municipal</strong><div class="report-actions"><button class="btn btn-small" id="muni-modo">Somente alertas</button><button class="btn btn-primary btn-small" id="muni-pdf">${icon('print')} Exportar PDF</button><button class="report-close" id="report-close" aria-label="Fechar relatório">${icon('close')}</button></div></div>${corpo}`;
 dialog.showModal();
 $('#report-close').onclick=()=>dialog.close();
 let modo='completo';
 $('#muni-modo').onclick=()=>{
  // troca o conteúdo entre relatório completo e só alertas; o PDF sai do que estiver na tela
  modo=modo==='completo'?'alertas':'completo';
  dialog.querySelector('.report-body').outerHTML=modo==='alertas'?corpoAlertas:corpo;
  $('#muni-modo').textContent=modo==='alertas'?'Relatório completo':'Somente alertas';
 };
 $('#muni-pdf').onclick=()=>{const t=document.title;document.title=`Curupira_${modo==='alertas'?'Alertas':'Relatorio'}_${m.name}`;window.print();document.title=t;};
 if($('#muni-json'))$('#muni-json').onclick=()=>downloadBlob(JSON.stringify({fonte:'SICAR',referencia:'2026-11-05',municipio:m,filtro_status:state.status||null,registros:out},null,2),`Curupira_CAR_${code}.json`);
}
