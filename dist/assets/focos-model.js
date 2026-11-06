(function(root){
 'use strict';
 function classify(value,limits){if(value===null)return -1;return limits.findIndex(n=>value<=n)===-1?limits.length:limits.findIndex(n=>value<=n);}
 function monthsBetween(start,end){const [y,m]=start.split('-').map(Number),[ey,em]=end.split('-').map(Number);const out=[];for(let i=y*12+m-1;i<=ey*12+em-1;i++)out.push(`${Math.floor(i/12)}-${String(i%12+1).padStart(2,'0')}`);return out;}
 function periods(manifest,mode,year,month){if(mode==='latest')return monthsBetween(manifest.default_period.start,manifest.default_period.end);return Object.keys(manifest.coverage).filter(p=>p.startsWith(`${year}-`)&&(mode==='year'||p===`${year}-${String(month).padStart(2,'0')}`)).sort();}
 function aggregate(index,files,periods,coverage){if(!periods.length)throw Error('Período sem dados disponíveis.');for(const p of periods)if(!coverage[p])throw Error('Período indisponível: '+p);return index.map((m,i)=>m.kind==='operacional'?null:periods.reduce((sum,p)=>{const [y,month]=p.split('-');const f=files[y];if(!f||f.months[+month-1]==='unavailable')throw Error('Contagem indisponível: '+p);return sum+f.monthly[i][+month-1];},0));}
 const labels=['0','1–10','11–50','51–200','201–1.000','1.001–5.000','> 5.000'];
 const latestYear=manifest=>Object.keys(manifest.years).sort().at(-1);
 function yearInfo(manifest,year){const available=periods(manifest,'year',year);return {partial:available.length<12||available.some(p=>manifest.coverage[p].status!=='complete'),date:manifest.as_of.split('-').reverse().join('/')};}
 function yearLabel(manifest,year){const info=yearInfo(manifest,year);return year+(info.partial?' · parcial até '+info.date:'');}
 function choroplethStyle(value,manifest,opacity=.65){const c=classify(value,manifest.classes);return {fillColor:c<0?'#a5b3b6':manifest.class_colors[c],color:'#526f5c',weight:.25,opacity:.65,fillOpacity:opacity};}
 function municipalityValue(index,data,code){const i=index.findIndex(m=>m.code===code);return i<0||index[i].kind==='operacional'?null:data.annual[i]??null;}
 function legacyTarget(search,latest){const q=new URLSearchParams(search),candidate=q.get('focos_ano')||q.get('year')||q.get('ano');const year=/^\d{4}$/.test(candidate||'')?candidate:latest;const next=new URLSearchParams({focos:'on'});if(year){next.set('focos_ano',year);next.set('focos_periodo','year');}const mode=q.get('focos_periodo')||q.get('period');if(['latest','year','month'].includes(mode))next.set('focos_periodo',mode);const month=q.get('focos_mes')||q.get('month');if(/^(0?[1-9]|1[0-2])$/.test(month||''))next.set('focos_mes',String(+month));if(/^\d{7}$/.test(q.get('municipio')||''))next.set('municipio',q.get('municipio'));return 'mapa.html?'+next;}
 const api={classify,monthsBetween,periods,aggregate,labels,latestYear,yearInfo,yearLabel,choroplethStyle,municipalityValue,legacyTarget};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.FocosModel=api;
})(typeof window==='undefined'?globalThis:window);
