/* script.js — injects loading screen */
(function () {
  function inject() {
    var el = document.createElement('div');
    el.id = 'page-loader';
    el.innerHTML = '<div class="pl-logo">RECRUTO</div><div class="pl-track"><div class="pl-fill"></div></div>';
    document.body.insertBefore(el, document.body.firstChild);
  }
  if (document.body) inject();
  else document.addEventListener('DOMContentLoaded', inject);
})();