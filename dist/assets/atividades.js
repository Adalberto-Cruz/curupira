/* Atalhos de contexto sobre as camadas existentes; não classificam uso do solo. */
(function(root){
 'use strict';
 const groups={
  ATIVIDADE_DESMATAMENTO:{label:'Desmatamento (todas as classes)',classes:['DESMATAMENTO_CR','DESMATAMENTO_VEG']},
  ATIVIDADE_CORTE_SELETIVO:{label:'Corte seletivo (todas as variantes)',classes:['CS_DESORDENADO','CS_GEOMETRICO','CORTE_SELETIVO']}
 };
 const definitions=[
  {id:'ti',label:'Terras Indígenas',layers:['ti'],category:''},
  {id:'desmatamento',label:'Desmatamento',layers:['prodes','deter'],category:'ATIVIDADE_DESMATAMENTO'},
  {id:'fogo',label:'Focos de calor e queimadas',layers:['deter'],category:'CICATRIZ_DE_QUEIMADA',focos:true},
  {id:'embargos',label:'Áreas embargadas',layers:['embargos'],category:''},
  {id:'madeira',label:'Exploração madeireira',layers:['deter'],category:'ATIVIDADE_CORTE_SELETIVO'},
  {id:'mineracao',label:'Garimpo e mineração',layers:['deter','anm'],category:'MINERACAO'}
 ];
const descricoes={"ti": "Mostra os limites das Terras Indígenas (FUNAI) no município. Imóvel do CAR sobre TI é sinal de alerta.", "desmatamento": "Mostra o desmatamento anual do PRODES e os alertas DETER de desmatamento (corte raso e com vegetação).", "fogo": "Mostra cicatrizes de queimada do DETER e liga os focos de calor do INPE. Foco é detecção de calor, não área queimada.", "embargos": "Mostra as áreas embargadas por órgão ambiental (IPAAM/Ibama) no município.", "madeira": "Mostra alertas DETER de corte seletivo (retirada de madeira sem derrubar toda a floresta).", "mineracao": "Mostra alertas DETER de mineração e os processos minerários da ANM no município."};
 function matchesClass(category,filter){return !filter||(groups[filter]?groups[filter].classes.includes(category):category===filter);}
 function plan(id,current){
  const definition=definitions.find(d=>d.id===id);
  if(!definition||definition.disabled)throw Error('Em desenvolvimento');
  if(!current.municipio)throw Error('Selecione um município');
  if(!/^13\d{5}$/.test(current.municipio))throw Error('Contexto ambiental disponível somente para municípios do Amazonas.');
  return {...current,camadas:[...new Set([...current.camadas,...definition.layers])],classe:definition.category,
   focos:!!current.focos||!!definition.focos};
 }
 function install({panel,getState,apply,hasMunicipality}){
  const section=document.createElement('section');section.className='layer-group activity-filters';
  section.setAttribute('aria-label','Filtros por atividade');
  section.innerHTML=`<h3 class="panel-heading">Filtros por atividade</h3><p>Atalhos para o contexto do município no AM. Outras camadas ligadas são mantidas; a classe DETER é substituída pelo atalho escolhido.</p><div class="activity-buttons">${definitions.map(d=>`<button type="button" data-activity="${d.id}"${d.disabled?' disabled':''}><span>${d.label}</span>${d.disabled?'<small>Em desenvolvimento</small>':''}</button>`).join('')}</div><p id="activities-status" role="status" aria-live="polite">Selecione um município para usar os atalhos.</p><p>Alertas e cruzamentos não comprovam atividade observada ou infração.</p>`;
  panel.insertBefore(section,panel.querySelector('.layer-group'));
  const buttons=[...section.querySelectorAll('button:not(:disabled)')],status=section.querySelector('#activities-status');
  let busy=false;
  for(const button of buttons)button.onclick=async()=>{
   if(busy)return;
   const current=getState();
   if(!current.municipio){status.textContent='Selecione um município';return;}
   if(!hasMunicipality(current.municipio)){status.textContent='Contexto ambiental disponível somente para municípios do Amazonas.';return;}
   const definition=definitions.find(d=>d.id===button.dataset.activity);
   const next=plan(definition.id,current);
   busy=true;buttons.forEach(b=>b.disabled=true);status.textContent='Aplicando '+definition.label+'…';
   try{
    await apply(next);
    status.textContent=definition.label+': '+(descricoes[definition.id]||'')+' Veja a contagem ao lado de cada camada.';
   }catch{
    status.textContent='Não foi possível concluir o atalho. Confira as camadas e tente novamente.';
   }finally{busy=false;buttons.forEach(b=>b.disabled=false);}
  };
  return section;
 }
 const api={groups,definitions,matchesClass,plan,install};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AngelimActivities=api;
})(typeof window==='undefined'?globalThis:window);
