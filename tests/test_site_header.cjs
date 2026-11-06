const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const H=require('../dist/assets/site-header.js');
test('três páginas compartilham menu sem Focos Brasil e mantêm o logo',()=>{
 for(const page of ['home','map','data']){const html=H.render(page);assert.ok(html.includes(H.brand()));for(const url of ['index.html','mapa.html','dados.html'])assert.ok(html.includes(`href="${url}"`));assert.equal((html.match(/aria-current="page"/g)||[]).length,1);assert.ok(!html.includes('Focos Brasil'));}
 assert.ok(!fs.readFileSync(path.join(__dirname,'../dist/assets/site-header.js'),'utf8').includes("page==='focos'"));
});
test('cabeçalho precede aplicativos e a página antiga somente redireciona',()=>{
 for(const name of ['index','mapa','dados']){const html=fs.readFileSync(path.join(__dirname,'../dist',name+'.html'),'utf8');assert.ok(html.indexOf('src="assets/site-header.js')<html.indexOf('src="assets/app.js'));}
 const legacy=fs.readFileSync(path.join(__dirname,'../dist/focos.html'),'utf8');assert.match(legacy,/focos-redirect.js/);assert.ok(!legacy.includes('id="map"'));
});
