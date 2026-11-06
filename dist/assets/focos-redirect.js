/* Compatibilidade dos links da antiga página; só lê o manifesto se faltar o ano. */
(async()=>{
 let latest='';const query=new URLSearchParams(location.search);
 if(!/^\d{4}$/.test(query.get('focos_ano')||query.get('year')||query.get('ano')||'')){
  try{const response=await fetch('data/focos-brasil/manifesto.json');if(response.ok)latest=FocosModel.latestYear(await response.json());}catch{/* O mapa exibirá a falha e permitirá continuar usando as outras camadas. */}
 }
 location.replace(FocosModel.legacyTarget(location.search,latest));
})();
