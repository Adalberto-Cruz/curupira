/* Camada nacional 2c-1b. A criação dos controles não lê arquivos de dados. */
'use strict';
let nationalFocos;
function installNationalFocos(){
 const store=FocosBrasil.createStore(),checkbox=$('#layer-focos-brasil'),controls=$('#focos-controls'),yearSelect=$('#focos-year'),modeSelect=$('#focos-period'),monthSelect=$('#focos-month'),status=$('#focos-status');
 let enabled=false,year='',mode='latest',month='',periodLabel='',selection='',data,layer,highlight,revision=0,selectionRevision=0,values=[];
 for(const [name,z] of [['focos-brasil',350],['focos-municipality',395]]){const pane=map.createPane(name);pane.style.zIndex=z;pane.style.pointerEvents='none';}
 const renderer=L.canvas({pane:'focos-brasil'}),highlightRenderer=L.canvas({pane:'focos-municipality'});
 const count=value=>value===null?'sem dado':fmt(value);
 const selectedValue=()=>{const i=data?.index.findIndex(m=>m.code===selection);return i===undefined||i<0?null:values[i]??null;};
 function remove(){if(layer)map.removeLayer(layer);if(highlight)map.removeLayer(highlight);highlight=null;}
 function updateHighlight(){
  if(highlight)map.removeLayer(highlight);highlight=null;
  if(!enabled||!data||!selection)return;
  const feature=data.geo.features.find(f=>f.id===selection);if(!feature)return;
  highlight=L.geoJSON(feature,{pane:'focos-municipality',renderer:highlightRenderer,interactive:false,style:{color:mapPalette.municipalities.selectedColor,weight:3,fillOpacity:0}}).addTo(map);
 }
 function fit(){if(enabled&&layer)map.fitBounds(layer.getBounds(),{padding:[16,16]});}
 function fitSelection(){if(highlight)map.fitBounds(highlight.getBounds(),{padding:[24,24],maxZoom:12});else fit();}
 function style(feature){return FocosModel.choroplethStyle(values[feature.properties.i],data.manifest,environmentalFilters.opacity);}
 function applyOpacity(){if(enabled&&layer)layer.setStyle(style);}
 function fail(error){
  console.error('Falha na camada Focos Brasil:',error);
  revision++;selectionRevision++;enabled=false;checkbox.checked=false;controls.hidden=true;remove();document.body.classList.remove('focos-active');
  status.textContent='Não foi possível carregar os focos agora. Tente marcar a camada de novo.';status.hidden=false;
  countyLayer.setStyle(countyStyle);renderTerritory();renderMapLegend();if(mapHistoryReady)writeMapURL(selectedProperty?.code||'',{replace:true});
 }
 function renderSelection(){
  let target=$('#focos-municipality');if(!target)return;
  const token=++selectionRevision;if(!enabled||!selection){target.hidden=true;return;}
  target.hidden=false;
  if(!data||!values.length){target.textContent='Carregando contagem de focos…';return;}
  const unit=data.index.find(m=>m.code===selection),name=unit?unit.name+' · '+unit.uf:selection;
  target.innerHTML=`<h3>Focos de calor · ${esc(name)}</h3><strong class="focos-year-count">${count(selectedValue())}</strong><p>${esc(periodLabel)} · satélite de referência</p><div id="focos-series" role="status">Carregando série anual…</div>`;
  store.series(selection).then(rows=>{
   if(!enabled||token!==selectionRevision)return;
   const output=$('#focos-series');if(!output)return;
   const maximum=Math.max(1,...rows.map(r=>r.value||0));
   const bars=rows.map((r,i)=>`<rect x="${i*10}" y="${40-(r.value===null?0:r.value/maximum*38)}" width="7" height="${r.value===null?0:r.value/maximum*38}"><title>${esc(r.label)}: ${count(r.value)}</title></rect>`).join('');
   output.innerHTML=`<svg class="focos-series" viewBox="0 0 ${rows.length*10} 42" role="img" aria-label="Série anual de focos ${rows[0].year} a ${rows.at(-1).year}">${bars}</svg><details><summary>Série anual ${rows[0].year}–${rows.at(-1).year}</summary><div class="focos-series-table"><table><thead><tr><th>Ano</th><th>Focos</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.label)}</td><td>${count(r.value)}</td></tr>`).join('')}</tbody></table></div></details><p>Focos não são incêndios únicos ou área queimada. Ano parcial não equivale a um ano fechado.</p>`;
  }).catch(error=>{if(enabled&&token===selectionRevision)fail(error);});
 }
 function select(code){selection=code||'';updateHighlight();if(enabled&&data){const unit=data.index.find(m=>m.code===selection);$('#map-top-text').textContent=unit?unit.name+' · Focos · '+periodLabel:'Brasil · Focos · '+periodLabel;}}
 function foreignPanel(){
  if(!enabled||!selection||muni(selection))return false;
  const unit=data?.index.find(m=>m.code===selection),name=unit?unit.name+' · '+unit.uf:selection;
  $('#territory-panel').innerHTML=`<div class="territory-top"><span class="state-code">MUNICÍPIO / BRASIL</span><span class="pill grey">IBGE ${esc(selection)}</span></div><h2>${esc(name)}</h2><p>${esc(HibamaMapState.coverageMessage(mapCARCoverage))}</p><section id="focos-municipality"></section>`;
  renderSelection();return true;
 }
 async function setEnabled(next,options={}){
  const wasEnabled=enabled,token=++revision;enabled=next;checkbox.checked=next;controls.hidden=!next;document.body.classList.toggle('focos-active',next);
  $('#fit-state').setAttribute('aria-label',next?'Enquadrar todo o Brasil':'Enquadrar todo o Amazonas');
  if(next||wasEnabled){state.colorCounties=false;$('#color-counties').checked=false;}
  if(options.year!==undefined)year=String(options.year||'');
  if(options.mode!==undefined)mode=options.mode;
  if(options.month!==undefined)month=String(options.month||'');
  if(!next){selectionRevision++;remove();status.hidden=true;countyLayer.setStyle(countyStyle);renderTerritory();renderMapLegend();return true;}
  status.hidden=false;status.textContent='Carregando focos do Brasil…';
  try{
   data=await store.load();if(token!==revision)return false;
   const available=Object.keys(data.manifest.years).sort();
   if(!available.includes(year)){if(year)toast('Ano de focos indisponível; restaurado o ano mais recente.');year=FocosModel.latestYear(data.manifest);}
   yearSelect.innerHTML=available.map(y=>`<option value="${y}">${esc(FocosModel.yearLabel(data.manifest,y))}</option>`).join('');yearSelect.value=year;
   const months=FocosModel.periods(data.manifest,'year',year).map(p=>String(+p.slice(5)));
   if(!months.includes(month)){if(month&&mode==='month')toast('Mês de focos indisponível; restaurado o mês mais recente disponível.');month=months.at(-1)||'';}
   monthSelect.innerHTML=months.map(m=>`<option value="${m}">${m.padStart(2,'0')}${data.manifest.coverage[year+'-'+m.padStart(2,'0')].status==='provisional'?' · provisório':''}</option>`).join('');monthSelect.value=month;modeSelect.value=mode;
   $('#focos-year-label').hidden=mode==='latest';$('#focos-month-label').hidden=mode!=='month';
   $('#focos-class-legend').innerHTML=FocosModel.labels.map((label,i)=>`<span><i style="background:${data.manifest.class_colors[i]}"></i>${label}</span>`).join('')+'<span><i style="background:#a5b3b6"></i>Sem dado</span>';
   $('.focos-swatch').style.background=data.manifest.class_colors[4];
   const result=await store.period(mode,year,month);if(token!==revision)return false;values=result.values;
   const periods=result.periods,provisional=periods.some(p=>data.manifest.coverage[p].status==='provisional');
   periodLabel=(mode==='year'?FocosModel.yearLabel(data.manifest,year):mode==='month'?periods[0]:'Últimos 12 meses fechados · '+periods[0]+' a '+periods.at(-1))+' · UTC'+(provisional?' · PROVISÓRIO'+(data.manifest.coverage[periods.at(-1)].maximum_utc?' · até '+data.manifest.coverage[periods.at(-1)].maximum_utc.slice(0,10):''):'');
   if(layer)map.removeLayer(layer);
   layer=L.geoJSON(data.geo,{pane:'focos-brasil',renderer,interactive:false,style}).addTo(map);
   countyLayer.setStyle(countyStyle);select(selection);renderTerritory();renderMapLegend();
   status.textContent=`${fmt(values.reduce((sum,n)=>sum+(n||0),0))} focos · ${periodLabel} · INPE / IBGE 2025. Classes fixas, contagem absoluta.`;
   if(options.fit&&!selection)fit();return true;
  }catch(error){if(token===revision)fail(error);return false;}
 }
 checkbox.addEventListener('change',async()=>{const success=await setEnabled(checkbox.checked,{fit:true});if(success)writeMapURL();});
 for(const [control,key] of [[yearSelect,'year'],[modeSelect,'mode'],[monthSelect,'month']])control.addEventListener('change',async()=>{const success=await setEnabled(true,{[key]:control.value});if(success)writeMapURL();});
 $('#focos-fit').onclick=fit;
 nationalFocos={get enabled(){return enabled;},get year(){return year;},get mode(){return mode;},get month(){return mode==='month'?month:'';},get selection(){return selection;},get data(){return data;},setEnabled,applyOpacity,select,renderSelection,foreignPanel,fit,fitSelection,store};
}
async function selectNationalMunicipality(code,options={}){
 if(muni(code)){await selectMunicipality(code,'',{...options,fit:true});return;}
 await selectMunicipality('','',{...options,fit:false});
 nationalFocos.select(code);renderTerritory();nationalFocos.fitSelection();if(options.history!==false)writeMapURL();
}
