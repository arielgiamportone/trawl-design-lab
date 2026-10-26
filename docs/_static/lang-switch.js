// Enlace «English / Español» al mismo capítulo en el otro libro (el inglés vive en /en/).
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  const english = /\/en\/[^/]*$/.test(path);
  let page = path.split('/').pop() || 'intro.html';
  if (english && page === 'glossary.html') page = '02_nomenclatura.html';
  const href = english ? `../${page}` : `en/${page}`;
  const a = document.createElement('a');
  a.href = href;
  a.className = 'btn lang-switch';
  a.lang = english ? 'es' : 'en';
  a.textContent = english ? 'Español' : 'English';
  a.title = english ? 'Leer este capítulo en español' : 'Read this chapter in English';
  a.style.cssText = 'font-size:0.9rem;padding:0 0.6rem;align-self:center;white-space:nowrap';
  const bar = document.querySelector('.article-header-buttons') || document.querySelector('.header-article-items__end');
  if (bar) bar.prepend(a);
  else document.body.prepend(a);
});
