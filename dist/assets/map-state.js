/* Estado compartilhável e consultas locais, sem dependência de DOM ou serviços. */
(function(root){
 'use strict';
 const layerIds=['municipios','car','ti','anm','embargos','prodes','deter'];
 const keys=['municipio','car','camadas','inicio','fim','classe','opacidade','base','colorir'];
 const defaults=()=>({municipio:'',car:'',camadas:['municipios','car','ti','deter'],inicio:'',fim:'',classe:'',opacidade:65,base:'satellite',colorir:false,focos:false,focos_ano:'',focos_periodo:'latest',focos_mes:''});
 const normalize=value=>String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/[·,/]+/g,' ').replace(/\s+/g,' ').trim();
 function coverage(catalog){
  const ufs=catalog.car_ufs;
  if(!Array.isArray(ufs)||!ufs.length||new Set(ufs).size!==ufs.length||ufs.some(uf=>typeof uf!=='string'||! /^[A-Z]{2}$/.test(uf)))throw Error('Cobertura CAR ausente ou inválida em data/catalogo.json (car_ufs).');
  return {ufs:[...ufs]};
 }
 const coverageMessage=config=>'CAR disponível somente nas UFs: '+new Intl.ListFormat('pt-BR',{type:'conjunction'}).format(config.ufs)+'.';
 const supportsUF=(config,uf)=>config.ufs.includes(uf);
 const carUF=value=>String(value).match(/^([A-Z]{2})-\d{7}-[A-F0-9]{32}$/i)?.[1].toUpperCase()||'';
 const isCarCode=(value,config)=>supportsUF(config,carUF(value));
 function validDate(value){if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;const date=new Date(value+'T00:00:00Z');return Number.isFinite(+date)&&date.toISOString().slice(0,10)===value&&value<='2026-11-05';}
 function decode(query,context){
  const params=new URLSearchParams(query),state=defaults(),warnings=[];
  if(!params.size)return {state,warnings};
  if(keys.some(k=>params.has(k))&&keys.some(k=>!params.has(k)))warnings.push('Filtros ausentes no link foram restaurados para o padrão.');
  for(const key of params.keys())if(![...keys,'focos','focos_ano','focos_periodo','focos_mes'].includes(key))warnings.push('Parâmetro desconhecido removido: '+key);
  const get=key=>{if(params.getAll(key).length>1){warnings.push('Parâmetro repetido restaurado: '+key);return null;}return params.get(key);};
  const invalid=key=>warnings.push('Filtro inválido restaurado: '+key);
  const focus=get('focos');if(focus!==null){if(['on','off'].includes(focus))state.focos=focus==='on';else invalid('focos');}
  const focusYear=get('focos_ano');if(focusYear){if(/^(19|20)\d{2}$/.test(focusYear))state.focos_ano=focusYear;else invalid('focos_ano');}
  const focusMode=get('focos_periodo');if(focusMode!==null){if(['latest','year','month'].includes(focusMode))state.focos_periodo=focusMode;else invalid('focos_periodo');}else if(state.focos_ano)state.focos_periodo='year';
  const focusMonth=get('focos_mes');if(focusMonth){if(/^(0?[1-9]|1[0-2])$/.test(focusMonth))state.focos_mes=String(+focusMonth);else invalid('focos_mes');}
  const municipality=get('municipio');
  if(municipality){if(context.municipalities.has(municipality)||state.focos&&context.nationalMunicipalities?.has(municipality))state.municipio=municipality;else invalid('municipio');}
  const car=get('car');
  if(car){const code=car.toUpperCase().replace(/\s/g,'');const municipality=context.carMunicipality(code);if(isCarCode(code,context.coverage)&&context.municipalities.has(municipality)){
    if(state.municipio&&state.municipio!==municipality)invalid('car (município incompatível)');else {state.car=code;state.municipio=municipality;}
   }else invalid('car');}
  const layers=get('camadas');if(layers!==null){const entries=layers?layers.split(','):[];if(entries.includes('focos')){state.focos=true;entries.splice(entries.indexOf('focos'),1);warnings.push('A camada antiga de focos foi substituída pela série nacional; as datas ambientais não se aplicam a ela.');}if(new Set(entries).size!==entries.length||entries.some(id=>!layerIds.includes(id)))invalid('camadas');else state.camadas=layerIds.filter(id=>entries.includes(id));}
  for(const key of ['inicio','fim']){const value=get(key);if(value){if(validDate(value))state[key]=value;else invalid(key);}}
  if(state.inicio&&state.fim&&state.inicio>state.fim){state.inicio=state.fim='';invalid('intervalo de datas');}
  const category=get('classe');if(category){if(context.categories.has(category))state.classe=category;else invalid('classe');}
  const opacity=get('opacidade');if(opacity!==null){if(/^\d+$/.test(opacity)&&+opacity>=10&&+opacity<=100)state.opacidade=+opacity;else invalid('opacidade');}
  const base=get('base');if(base!==null){if(['satellite','terrain'].includes(base))state.base=base;else invalid('base');}
  const color=get('colorir');if(color!==null){if(['0','1'].includes(color))state.colorir=color==='1';else invalid('colorir');}
  return {state,warnings:[...new Set(warnings)]};
 }
 function serialize(state){
  const normal={...state,camadas:layerIds.filter(id=>state.camadas.includes(id)),focos:!!state.focos,focos_ano:state.focos?String(state.focos_ano||''):'',focos_periodo:state.focos?(state.focos_periodo||'latest'):'latest',focos_mes:state.focos&&state.focos_periodo==='month'?String(state.focos_mes||''):''};
  if([...keys,'focos','focos_ano','focos_periodo','focos_mes'].every(key=>JSON.stringify(normal[key])===JSON.stringify(defaults()[key])))return '';
  const params=new URLSearchParams();for(const key of keys)params.set(key,key==='camadas'?normal.camadas.join(','):key==='colorir'?(normal.colorir?'1':'0'):String(normal[key]));if(normal.focos){params.set('focos','on');if(normal.focos_ano)params.set('focos_ano',normal.focos_ano);params.set('focos_periodo',normal.focos_periodo);if(normal.focos_mes)params.set('focos_mes',normal.focos_mes);}return '?'+params;
 }
 function search(entries,value,limit=12,config={ufs:[]}){const query=normalize(value);if(!query)return [];
  return entries.filter(m=>normalize(m.name+' '+m.uf).includes(query)||m.code===query).sort((a,b)=>{
   const rank=m=>normalize(m.name)===query?0:normalize(m.name).startsWith(query)?1:2;
   return rank(a)-rank(b)||(supportsUF(config,a.uf)?0:1)-(supportsUF(config,b.uf)?0:1)||a.name.localeCompare(b.name,'pt-BR')||a.uf.localeCompare(b.uf);
  }).slice(0,limit);
 }
 function ringContains(ring,x,y){let inside=false;for(let i=0,j=ring.length-1;i<ring.length;j=i++){
  const [ax,ay]=ring[j],[bx,by]=ring[i],cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax);
  if(Math.abs(cross)<1e-10&&x>=Math.min(ax,bx)-1e-10&&x<=Math.max(ax,bx)+1e-10&&y>=Math.min(ay,by)-1e-10&&y<=Math.max(ay,by)+1e-10)return 2;
  if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;
 }return inside?1:0;}
 function covers(geometry,x,y){const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.type==='MultiPolygon'?geometry.coordinates:[];
  return polygons.some(rings=>{const outer=ringContains(rings[0],x,y);if(outer===2)return true;if(!outer)return false;for(const hole of rings.slice(1)){const hit=ringContains(hole,x,y);if(hit===2)return true;if(hit===1)return false;}return true;});
 }
 const api={defaults,layerIds,decode,serialize,normalize,search,covers,validDate,coverage,coverageMessage,supportsUF,carUF,isCarCode};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.HibamaMapState=api;
})(typeof window==='undefined'?globalThis:window);
