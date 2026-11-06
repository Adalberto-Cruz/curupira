/* Indicador de pressão sobre a água: lê o JSON estático e mostra no painel de camadas. */
(function(root){
 'use strict';
 let data=null,loading=null;
 const nomes={mineracao_deter:'Alertas DETER de mineração',anm_extracao:'Títulos ANM com extração',desmatamento_recente:'Desmatamento recente (PRODES 2023–2025 + DETER 3 anos)'};
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function html(code,doc){
  // Sem município ou fora do AM: mensagem simples, nunca um número inventado.
  if(!code)return '<p class="panel-note">Selecione um município.</p>';
  const m=doc&&doc.municipios&&doc.municipios[code];
  if(!m)return '<p class="panel-note">Indicador disponível somente para municípios do Amazonas.</p>';
  const linhas=Object.keys(nomes).map(k=>`<li>${escape(nomes[k])}: <b>${escape(m.contagens[k])}</b></li>`).join('');
  return `<p class="water-score water-${escape(m.classe==='média'?'media':m.classe)}"><b>${escape(m.score)}</b>/100 · pressão ${escape(m.classe)}</p><ul class="water-parts">${linhas}</ul><p class="panel-note">${escape(doc.aviso)} Escala relativa entre os 62 municípios do AM. Não é laudo nem medição de qualidade da água.</p>`;
 }
 async function load(){
  if(data)return data;
  if(!loading)loading=fetch('data/agua/indicador.json?v=1.0.0').then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json();});
  try{data=await loading;}catch(e){loading=null;throw e;}
  return data;
 }
 function box(){
  let el=document.getElementById('water-indicator');
  if(el)return el;
  const panel=document.querySelector('.layer-panel');if(!panel)return null;
  el=document.createElement('section');el.className='layer-group water-indicator';el.id='water-indicator';
  el.setAttribute('aria-live','polite');
  el.innerHTML='<div class="panel-heading">PRESSÃO SOBRE A ÁGUA</div><div id="water-body"></div>';
  panel.insertBefore(el,panel.querySelector('.layer-info'));
  return el;
 }
 async function render(code){
  const el=box();if(!el)return;
  const body=el.querySelector('#water-body');
  if(!code){body.innerHTML=html('',null);return;}
  body.innerHTML='<p class="panel-note">Carregando indicador…</p>';
  try{const doc=await load();body.innerHTML=html(code,doc);}
  catch{body.innerHTML='<p class="panel-note">Indicador indisponível. Recarregue a página.</p>';}
 }
 const api={html,render,load};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AngelimAgua=api;
})(typeof window==='undefined'?globalThis:window);
