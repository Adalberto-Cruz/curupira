/* Dados da 2c-1: leitura gzip, integridade e cache compartilhados; sem carga automática. */
(function(root){
 'use strict';
 function createStore(options={}){
  const model=options.model||root.FocosModel;
  const fetcher=options.fetcher||((...args)=>fetch(...args)),base=options.base||'data/focos-brasil/';
  const files=new Map(),pending=new Map(),transfers=new Map();let manifestPromise,basePromise;
  async function read(path,descriptor){
   const response=await fetcher(base+path);if(!response.ok)throw Error(`Arquivo ${path} indisponível (${response.status}). Restaure os produtos locais.`);
   const bytes=await response.arrayBuffer();if(descriptor&&bytes.byteLength!==descriptor.bytes)throw Error('Tamanho inesperado: '+path);
   if(descriptor&&globalThis.crypto?.subtle){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==descriptor.sha256)throw Error('Integridade inválida: '+path);}
   let payload;if(path.endsWith('.gz')){if(!globalThis.DecompressionStream)throw Error('Este navegador precisa de suporte a gzip.');payload=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}else payload=new TextDecoder().decode(bytes);
   transfers.set(path,bytes.byteLength);return JSON.parse(payload);
  }
  function manifest(){if(!manifestPromise)manifestPromise=read('manifesto.json').then(m=>{if(m.version!==1||!m.years||!m.mesh||!m.index)throw Error('Manifesto de focos inválido.');return m;}).catch(error=>{manifestPromise=null;throw error;});return manifestPromise;}
  function load(){if(!basePromise)basePromise=manifest().then(async m=>{const [index,geo]=await Promise.all([read(m.index.path,m.index),read(m.mesh.path,m.mesh)]);if(index.units.length!==m.units||geo.features.length!==m.units)throw Error('Malha e índice de focos incompatíveis.');return {manifest:m,index:index.units,geo};}).catch(error=>{basePromise=null;throw error;});return basePromise;}
  async function year(y){y=String(y);if(files.has(y))return files.get(y);if(!pending.has(y))pending.set(y,manifest().then(m=>{if(!m.years[y])throw Error('Ano de focos indisponível: '+y);return read(m.years[y].path,m.years[y]);}).then(data=>{files.set(y,data);return data;}).finally(()=>pending.delete(y)));return pending.get(y);}
  async function period(mode,y,month){const data=await load(),periods=model.periods(data.manifest,mode,y,month),years=[...new Set(periods.map(p=>p.slice(0,4)))],loaded=await Promise.all(years.map(year));return {...data,periods,values:model.aggregate(data.index,Object.fromEntries(years.map((y,i)=>[y,loaded[i]])),periods,data.manifest.coverage)};}
  const annual=y=>period('year',y);
  async function series(code){const {manifest:m,index}=await load(),years=Object.keys(m.years).sort(),result=new Array(years.length);let cursor=0;await Promise.all(Array.from({length:4},async()=>{while(cursor<years.length){const i=cursor++,y=years[i];result[i]={year:y,value:model.municipalityValue(index,await year(y),code),label:model.yearLabel(m,y)};}}));return result;}
  return {manifest,load,year,period,annual,series,transfers};
 }
 const api={createStore};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.FocosBrasil=api;
})(typeof window==='undefined'?globalThis:window);
