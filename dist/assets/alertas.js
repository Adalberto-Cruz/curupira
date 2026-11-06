/* Visão de alertas: o mapa já abre mostrando onde estão os alertas DETER do AM.
   Longe: uma bolha por município. Perto (zoom 9+): cada alerta vira um ponto.
   Para conferir se o alerta cai dentro de um imóvel, a pessoa liga o CAR. */
(function(root){
 'use strict';
 const cores={critica:'#c62828',alta:'#e8711c',media:'#d9a21b',baixa:'#7d8fa0'};
 const nomesPr={critica:'Crítica',alta:'Alta',media:'Média',baixa:'Baixa'};
 const nomesClasse={DESMATAMENTO_CR:'Desmatamento (corte raso)',DESMATAMENTO_VEG:'Desmatamento com vegetação',CICATRIZ_DE_QUEIMADA:'Cicatriz de queimada',DEGRADACAO:'Degradação',MINERACAO:'Mineração',CS_DESORDENADO:'Corte seletivo desordenado',CS_GEOMETRICO:'Corte seletivo geométrico',CORTE_SELETIVO:'Corte seletivo'};
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const num=v=>Number(v).toLocaleString('pt-BR',{maximumFractionDigits:0});
 const ZOOM_PONTOS=9;
 function resumo(g){return `${g.total} alertas · ${g.por_prioridade.critica} críticos · ${num(g.ha)} ha`;}
 function bolhaHTML(g){const r=Math.round(16+Math.min(22,Math.sqrt(g.total)*1.4));return {html:`<span style="width:${r*2}px;height:${r*2}px;background:${cores[g.maior]}">${g.total}</span>`,r};}

 const br=d=>String(d).split('-').reverse().join('/');
 // monta o texto do painel da direita; ponto é opcional (quando clicou num alerta só)
 function painelHTML(doc,cod,ponto){
  const g=(doc.municipios||{})[cod];
  if(!g)return '<section id="alert-info" class="alert-info"><h3>Alertas</h3><p>Sem alertas DETER neste município nos últimos 6 meses.</p></section>';
  const meus=(doc.pontos||[]).filter(p=>p[2]===cod).sort((a,b)=>b[4]<a[4]?-1:1);
  const porClasse={};meus.forEach(p=>{porClasse[p[3]]=(porClasse[p[3]]||0)+1;});
  const classes=Object.entries(porClasse).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<li>${esc(nomesClasse[k]||k)}: <b>${v}</b></li>`).join('');
  const prior=Object.keys(cores).map(k=>`<span><i style="background:${cores[k]}"></i>${nomesPr[k]} <b>${g.por_prioridade[k]||0}</b></span>`).join('');
  const ultimos=meus.slice(0,5).map(p=>`<li>${esc(br(p[4]))} · ${esc(nomesClasse[p[3]]||p[3])} · ${esc(p[5])} ha</li>`).join('');
  const det=ponto?`<div class="alert-detail" style="border-left:4px solid ${cores[ponto[6]]}"><b>Alerta selecionado</b><br>${esc(nomesClasse[ponto[3]]||ponto[3])}<br>Data: ${esc(br(ponto[4]))} · Área: ${esc(ponto[5])} ha<br>Prioridade: ${esc(nomesPr[ponto[6]])} (${esc((doc.regra||{})[ponto[6]]||'')})<br>Local: ${esc(ponto[1].toFixed(4))}, ${esc(ponto[0].toFixed(4))}</div>`:'';
  const periodo=doc.periodo?`${br(doc.periodo[0])} a ${br(doc.periodo[1])}`:'últimos 6 meses';
  return `<section id="alert-info" class="alert-info"><h3>Alertas em ${esc(g.nome)}</h3>${det}<p><b>${g.total}</b> alertas DETER · <b>${num(g.ha)}</b> ha · ${esc(periodo)}</p><div class="alert-prior">${prior}</div><h4>O que está acontecendo</h4><ul>${classes}</ul><h4>Mais recentes</h4><ul>${ultimos}</ul><p class="panel-note">Para saber se o alerta está dentro de um imóvel, ligue "Imóveis do CAR" e aproxime o mapa. ${esc(doc.aviso||'')}</p></section>`;
 }
 function mostrarPainel(doc,cod,ponto){
  const alvo=document.getElementById('territory-panel');if(!alvo)return;
  const velho=document.getElementById('alert-info');if(velho)velho.remove();
  alvo.insertAdjacentHTML('afterbegin',painelHTML(doc,cod,ponto));
  alvo.scrollTop=0;
 }
 function start(L,map,doc,onMunicipio,onPonto=()=>{}){
  const bolhas=L.layerGroup(),pontos=L.layerGroup();
  for(const [cod,g] of Object.entries(doc.municipios||{})){
   const b=bolhaHTML(g);
   L.marker([g.y,g.x],{icon:L.divIcon({className:'alert-bubble',html:b.html,iconSize:[b.r*2,b.r*2]}),keyboard:true,title:g.nome})
    .bindTooltip(`<b>${esc(g.nome)}</b><br>${esc(resumo(g))}<br><small>Clique para abrir o município</small>`,{direction:'top'})
    .on('click',()=>onMunicipio(cod)).addTo(bolhas);
  }
  for(const [lon,lat,cod,classe,data,ha,pr] of doc.pontos||[]){
   L.circleMarker([lat,lon],{radius:5,weight:1,color:'#fff',fillColor:cores[pr]||cores.baixa,fillOpacity:.9})
    .bindTooltip(`<b>${esc(nomesClasse[classe]||classe)}</b><br>${esc(data.split('-').reverse().join('/'))} · ${esc(ha)} ha · prioridade ${esc(nomesPr[pr]||pr)}<br><small>Clique para ver os detalhes</small>`)
    .on('click',()=>onPonto([lon,lat,cod,classe,data,ha,pr])).addTo(pontos);
  }
  let ligado=true;
  function atualizar(){
   const perto=map.getZoom()>=ZOOM_PONTOS;
   [bolhas,pontos].forEach(l=>map.removeLayer(l));
   if(ligado)map.addLayer(perto?pontos:bolhas);
  }
  map.on('zoomend',atualizar);
  const legenda=L.control({position:'bottomleft'});
  legenda.onAdd=()=>{
   const d=L.DomUtil.create('div','alert-legend');
   d.innerHTML=`<label><input type="checkbox" id="alertas-toggle" checked> <b>Alertas DETER · últimos 6 meses</b></label><div>${Object.keys(cores).map(k=>`<span><i style="background:${cores[k]}"></i>${nomesPr[k]}</span>`).join('')}</div><small>${esc(doc.aviso||'')}</small>`;
   L.DomEvent.disableClickPropagation(d);
   d.querySelector('input').onchange=e=>{ligado=e.target.checked;atualizar();};
   return d;
  };
  legenda.addTo(map);
  atualizar();
  return {bolhas,pontos,atualizar};
 }
 // espera o mapa principal existir (ele é criado pelo app.js depois de carregar o catálogo)
 function boot(){
  if(typeof document==='undefined'||document.body.dataset.page!=='map')return;
  let tentativas=0;
  const t=setInterval(async()=>{
   tentativas++;
   let m=null;try{m=map;}catch{}
   if(!m||!m.getZoom){if(tentativas>100)clearInterval(t);return;}
   clearInterval(t);
   try{
    const r=await fetch('data/alertas/am-6meses.json?v=1.0.0');if(!r.ok)throw Error('HTTP '+r.status);
    const doc=await r.json();
    start(L,m,doc,async cod=>{
     // abre o município e depois coloca o resumo dos alertas no topo do painel
     try{if(typeof selectMunicipality==='function'&&selectedCode!==cod)await selectMunicipality(cod);}catch(e){console.error(e);}
     mostrarPainel(doc,cod);
    },ponto=>mostrarPainel(doc,ponto[2],ponto));
   }catch(e){console.error('Alertas indisponíveis',e);}
  },300);
 }
 const api={start,resumo,bolhaHTML,cores,boot,painelHTML};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else{root.CurupiraAlertas=api;document.addEventListener('DOMContentLoaded',boot);}
})(typeof window==='undefined'?globalThis:window);
