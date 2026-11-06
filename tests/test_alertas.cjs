// Testa a visão de alertas com um Leaflet falso (sem navegador).
const test=require('node:test'),assert=require('node:assert'),fs=require('fs');
const A=require('../dist/assets/alertas.js');
const doc=JSON.parse(fs.readFileSync('dist/data/alertas/am-6meses.json','utf8'));
function fakeL(){
 const made={markers:0,circles:0,controls:0};
 const layer=()=>({items:[],addTo(g){g.items.push(this);return this;},bindTooltip(){return this;},on(){return this;}});
 const L={made,
  layerGroup:()=>({items:[]}),
  marker:()=>{made.markers++;return layer();},
  circleMarker:()=>{made.circles++;return layer();},
  divIcon:o=>o,
  control:()=>({addTo(){made.controls++;}}),
  DomUtil:{create:()=>({})},DomEvent:{disableClickPropagation(){}}};
 return L;
}
function fakeMap(z){const on=[];return {z,added:[],getZoom(){return this.z;},on(e,f){on.push(f);},removeLayer(l){this.added=this.added.filter(x=>x!==l);},addLayer(l){this.added.push(l);},fire(){on.forEach(f=>f());}};}
test('dados: pontos dentro do AM e prioridades válidas',()=>{
 assert.ok(doc.pontos.length>100);
 for(const [lon,lat,cod,,data,ha,pr] of doc.pontos){assert.ok(lon>-74&&lon<-56&&lat>-10&&lat<3,'fora do AM: '+cod);assert.ok(/^13\d{5}$/.test(cod));assert.ok(data>=doc.periodo[0]&&data<=doc.periodo[1]);assert.ok(ha>=0);assert.ok(['critica','alta','media','baixa'].includes(pr));}
 const soma=Object.values(doc.municipios).reduce((a,g)=>a+g.total,0);assert.equal(soma,doc.pontos.length);
});
test('longe mostra bolhas, perto mostra pontos',()=>{
 const L=fakeL(),map=fakeMap(6),r=A.start(L,map,doc,()=>{});
 assert.equal(L.made.markers,Object.keys(doc.municipios).length);assert.equal(L.made.circles,doc.pontos.length);
 assert.deepEqual(map.added,[r.bolhas]);map.z=10;map.fire();assert.deepEqual(map.added,[r.pontos]);
});
test('arquivo vazio não quebra',()=>{const L=fakeL(),map=fakeMap(6);A.start(L,map,{},()=>{});assert.equal(L.made.markers,0);});
test('resumo do município',()=>{assert.equal(A.resumo({total:3,ha:12.4,por_prioridade:{critica:1}}),'3 alertas · 1 críticos · 12 ha');});
