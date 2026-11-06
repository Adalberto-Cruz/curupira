/* Índice estático por regras; não executa modelo de IA no navegador. */
(function(root){
 'use strict';
 const DISCLAIMER='Índice por regras sobre dados públicos. Não é laudo nem prova de infração. Modelo de IA (LightGBM) em desenvolvimento.';
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const number=(value,digits=1)=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:digits}).format(value);
 const codePattern=/^AM-13\d{5}-[0-9A-F]{32}$/;
 const labels={prodes:'Área PRODES no CAR',deter:'Alertas DETER por classe',anm:'Processos ANM',focos:'Focos da amostra AM',trava:'Complemento da trava crítica'};
 const lockLabels={ti:'Terra Indígena',embargos:'Embargo na cópia IPAAM'};
 function validateRow(row){
  if(!row||!Number.isFinite(row.nota)||row.nota<0||row.nota>100||!Array.isArray(row.travas)||row.travas.some(k=>!lockLabels[k]))throw Error('Índice inválido.');
  const values=Object.keys(labels).map(k=>row.contribuicoes?.[k]);
  if(values.some(v=>!Number.isFinite(v)||v<0)||Math.abs(values.reduce((s,n)=>s+n,0)-row.nota)>.051)throw Error('Contribuições incompatíveis.');
  if(row.travas.length&&row.nota!==100||!row.travas.length&&row.contribuicoes.trava!==0)throw Error('Trava incompatível.');
  if(!Number.isFinite(row.area_car_ha)||row.area_car_ha<=0||!Number.isFinite(row.prodes_no_car_ha)||row.prodes_no_car_ha<0||!Number.isFinite(row.fracao_prodes)||row.fracao_prodes<0||row.fracao_prodes>1)throw Error('Área de referência inválida.');
  return row;
 }
 function validateData(data,municipio){
  if(data?.municipio!==municipio||data.version!=='1.0.0'||data.disclaimer!==DISCLAIMER||!data.by_car||!Array.isArray(data.top20)||data.top20.length>20||new Set(data.top20).size!==data.top20.length)throw Error('Base de atenção incompatível.');
  for(const [code,row] of Object.entries(data.by_car)){if(!codePattern.test(code))throw Error('Código CAR inválido.');validateRow(row);}
  for(const code of data.top20)if(!data.by_car[code]||data.by_car[code].situacao==='CA'||data.by_car[code].nota<=0)throw Error('Ranking incompatível.');
  const expected=Object.keys(data.by_car).filter(c=>data.by_car[c].situacao!=='CA'&&data.by_car[c].nota>0).sort((a,b)=>data.by_car[b].nota-data.by_car[a].nota||(a<b?-1:a>b?1:0)).slice(0,20);
  if(JSON.stringify(expected)!==JSON.stringify(data.top20))throw Error('Ordenação do ranking incompatível.');
  return data;
 }
 function createStore(fetcher=(...args)=>fetch(...args),base='data/atencao/'){
  const cache=new Map();
  async function load(municipio){
   if(!/^13\d{5}$/.test(municipio))throw Error('Somente municípios do Amazonas.');
   if(!cache.has(municipio))cache.set(municipio,fetcher(base+'municipios/'+municipio+'.json').then(r=>{if(!r.ok)throw Error('Base indisponível.');return r.json();}).then(d=>validateData(d,municipio)).catch(e=>{cache.delete(municipio);throw e;}));
   return cache.get(municipio);
  }
  return {load};
 }
 const store=createStore();
 function detailHTML(row){
  validateRow(row);
  const locks=row.travas.map(k=>lockLabels[k]);
  const classes=Object.entries(row.classes_deter||{}).map(([c,n])=>escape(c)+': '+number(n,0)).join(' · ')||'Nenhum alerta cruzado na base';
  return `<div class="attention-card"><h3>Índice de atenção por CAR</h3><p class="attention-score${locks.length?' attention-critical':''}"><strong>${number(row.nota)}</strong><span>/ 100</span></p>${locks.length?`<p class="attention-critical"><strong>Trava crítica:</strong> ${locks.map(escape).join(' e ')}. A trava fixa a nota em 100; não se somam duas travas.</p>`:''}<p class="attention-disclaimer">${DISCLAIMER}</p><dl class="attention-factors">${Object.entries(labels).map(([key,label])=>`<div><dt>${label}</dt><dd>${number(row.contribuicoes[key])} pontos</dd></div>`).join('')}</dl><details><summary>Dados, pesos e limites</summary><p>PRODES no CAR: ${number(row.prodes_no_car_ha,4)} ha. Área geodésica do CAR: ${number(row.area_car_ha,4)} ha. Fração usada: ${number(row.fracao_prodes*100,2)}%. A área PRODES foi dissolvida antes da medição.</p><p>DETER: ${classes}.</p><p>Fontes locais: SICAR (05/11/2026), Funai, cópia de embargos IPAAM/Ibama, INPE PRODES/DETER e processos ANM. Focos: amostra AM de 29/10 a 04/11/2026, todos os satélites; não são incêndios únicos nem a série nacional. A vigência dos embargos não foi revalidada.</p><p>0 significa ausência de contribuição nestas bases e regras; não comprova regularidade ou ausência de alteração. Trava crítica indica prioridade de conferência, não conclusão jurídica. Cadastro cancelado mantém o índice no detalhe, mas fica fora do top 20.</p><p>Versão 1.0.0 · <a href="data/atencao/pesos.json" target="_blank" rel="noopener">Consultar pesos</a> · <a href="data/atencao/manifesto.json" target="_blank" rel="noopener">Fontes, períodos e hashes</a></p></details></div>`;
 }
 async function renderDetail(target,code,municipio,isCurrent=()=>true,source=store){
  if(!target)return;
  target.innerHTML='<p role="status">Carregando índice por regras…</p>';
  try{
   const data=await source.load(municipio);
   if(!isCurrent()||!target.isConnected)return;
   const row=data.by_car[code];
   if(!row)throw Error('CAR não encontrado na base de atenção.');
   target.innerHTML=detailHTML(row);
  }catch{
   if(!isCurrent()||!target.isConnected)return;
   target.innerHTML=`<p role="status">Índice indisponível. Isso não equivale a nota zero.</p><button class="btn btn-small" type="button">Tentar carregar índice</button>`;
   target.querySelector('button').onclick=()=>renderDetail(target,code,municipio,isCurrent,source);
  }
 }
 async function renderList(target,options,source=store){
  const {municipio,municipalities,onSelectMunicipality,onOpen,isCurrent}=options;
  target.innerHTML=`<section class="attention-list"><h2>Imóveis que pedem atenção</h2><p class="attention-disclaimer">${DISCLAIMER}</p><label>Município do Amazonas<select id="attention-municipality" aria-label="Município dos imóveis que pedem atenção"><option value="">Selecione um município</option>${municipalities.map(m=>`<option value="${escape(m.code)}"${m.code===municipio?' selected':''}>${escape(m.name)}</option>`).join('')}</select></label><p>Até 20 CARs com nota positiva, em ordem decrescente; empates pelo código. Cadastros cancelados não entram nesta lista. Prioridade de análise, sem julgamento de infração.</p><div id="attention-ranking" role="status">${municipio?'Carregando prioridades…':'Selecione um município para consultar a lista.'}</div></section>`;
  target.querySelector('#attention-municipality').onchange=e=>onSelectMunicipality(e.target.value);
  if(!municipio)return;
  try{
   const data=await source.load(municipio);
   if(!isCurrent()||!target.isConnected)return;
   const ranking=target.querySelector('#attention-ranking');
   ranking.innerHTML=data.top20.length?`<div class="table-wrap"><table><thead><tr><th>Código CAR</th><th>Nota / 100</th><th>Trava crítica</th><th></th></tr></thead><tbody>${data.top20.map(code=>{const r=data.by_car[code];return `<tr><td class="attention-code">${escape(code)}</td><td class="${r.nota>=75?'attention-critical':''}"><strong>${number(r.nota)}</strong></td><td>${r.travas.map(k=>escape(lockLabels[k])).join(' · ')||'—'}</td><td><button class="btn btn-small" type="button" data-attention-car="${escape(code)}">Abrir CAR</button></td></tr>`;}).join('')}</tbody></table></div>`:'Nenhum CAR com nota positiva nessas bases e regras. Isso não comprova ausência de ocorrências.';
   ranking.querySelectorAll('[data-attention-car]').forEach(b=>b.onclick=()=>onOpen(b.dataset.attentionCar));
  }catch{
   if(!isCurrent()||!target.isConnected)return;
   const ranking=target.querySelector('#attention-ranking');
   ranking.innerHTML='<p>Lista indisponível. Nenhuma nota foi presumida.</p><button class="btn btn-small" type="button">Tentar novamente</button>';
   ranking.querySelector('button').onclick=()=>renderList(target,options,source);
  }
 }
 const api={DISCLAIMER,createStore,validateRow,validateData,detailHTML,renderDetail,renderList};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.AngelimAttention=api;
})(typeof window==='undefined'?globalThis:window);
