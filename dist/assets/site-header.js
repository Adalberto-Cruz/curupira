/* Cabeçalho único das páginas públicas; independente dos catálogos e do mapa. */
(function(root){
 'use strict';
 const brand=()=>`<a class="brand" href="index.html" aria-label="Curupira, início"><span class="brand-mark"><img src="assets/curupira-mark.png" alt=""></span><span>CURUPIRA<span class="brand-dot">.</span></span></a>`;
 const pages=[['home','index.html','Início'],['map','mapa.html','Mapa interativo'],['data','dados.html','Dados & CAR']];
 function render(page){return `<header class="header">${brand()}<nav class="nav" aria-label="Navegação principal">${pages.map(([id,url,label])=>`<a href="${url}" class="${page===id?'active':''}"${page===id?' aria-current="page"':''}>${label}</a>`).join('')}</nav><div class="header-actions"><span class="snapshot"><span class="dot"></span>Base de 05 nov. 2026</span><a class="btn ${page==='home'?'btn-primary':'btn-small'}" href="${page==='map'?'dados.html':'mapa.html'}">${page==='map'?'Consultar CAR':'Explorar território'} <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h16m-6-6 6 6-6 6"/></svg></a></div></header>`;}
 const api={brand,render};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.HibamaHeader=api;
})(typeof window==='undefined'?globalThis:window);
