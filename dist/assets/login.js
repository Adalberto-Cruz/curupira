/* Login para exportar: todo botão de exportar/baixar pede usuário e senha antes.
   Versão de demonstração (admin/admin). Num site estático isso não é segurança de
   verdade, só uma barreira; o certo depois é login no servidor (ex.: Amazon Cognito). */
(function(root){
 'use strict';
 const BOTOES=['export-data','export-map','download-geometry','report-download','report-print','env-export'];
 const CHAVE='curupira-login';
 function confere(u,s){return String(u).trim().toLowerCase()==='admin'&&String(s)==='admin';}
 function logado(){try{return sessionStorage.getItem(CHAVE)==='1';}catch{return false;}}
 function marcar(){try{sessionStorage.setItem(CHAVE,'1');}catch{}}
 function dialogo(){
  let d=document.getElementById('login-dialog');if(d)return d;
  d=document.createElement('dialog');d.id='login-dialog';d.className='login-dialog';
  d.innerHTML='<form method="dialog"><h2>Entrar para exportar</h2><p>Exportar dados e relatórios exige login.</p><label>Usuário<input name="u" autocomplete="username" required></label><label>Senha<input name="s" type="password" autocomplete="current-password" required></label><p class="login-erro" role="alert" hidden>Usuário ou senha incorretos.</p><div class="login-acoes"><button type="button" class="btn btn-small" value="cancelar">Cancelar</button><button class="btn btn-primary btn-small" value="ok">Entrar</button></div></form>';
  document.body.append(d);
  d.querySelector('[value=cancelar]').onclick=()=>d.close();
  return d;
 }
 function pedir(depois){
  const d=dialogo(),f=d.querySelector('form'),erro=d.querySelector('.login-erro');
  erro.hidden=true;f.reset();
  f.onsubmit=e=>{
   e.preventDefault();
   if(!confere(f.u.value,f.s.value)){erro.hidden=false;f.s.value='';f.s.focus();return;}
   marcar();d.close();depois();
  };
  d.showModal();f.u.focus();
 }
 function instalar(){
  // escuta na fase de captura: roda antes do clique chegar no botão
  document.addEventListener('click',e=>{
   const b=e.target.closest&&e.target.closest(BOTOES.map(id=>'#'+id).join(','));
   if(!b||logado())return;
   e.preventDefault();e.stopImmediatePropagation();
   pedir(()=>b.click());
  },true);
 }
 const api={confere,BOTOES};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 else{root.CurupiraLogin=api;document.addEventListener('DOMContentLoaded',instalar);}
})(typeof window==='undefined'?globalThis:window);
