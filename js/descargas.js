// descargas.js — agrega un botón «Descargar» debajo de cada tabla del sitio.
// Arma un CSV que Excel abre directo (separador «;», coma decimal, UTF-8). Los montos van
// con su valor exacto en millones de pesos (atributo data-n) y no con el texto abreviado.
(function () {
  const limpiar = (t) => t.replace(/\s*\n\s*/g, ' · ').replace(/\s+/g, ' ').trim();
  const celda = (v) => '"' + String(v).replace(/"/g, '""') + '"';
  function csv(tabla) {
    const filas = [...tabla.rows];
    const conMonto = new Set();
    filas.forEach((tr) => [...tr.cells].forEach((c, i) => { if (c.querySelector('[data-n]')) conMonto.add(i); }));
    return filas.map((tr, r) => [...tr.cells].map((c, i) => {
      const n = c.querySelector('[data-n]');
      if (n && r > 0) return celda(n.dataset.n.replace('.', ','));
      const t = limpiar(c.innerText || c.textContent);
      return celda(r === 0 && conMonto.has(i) ? t + ' (millones de $)' : t);
    }).join(';')).join('\r\n');
  }
  function nombre(tabla, i) {
    const base = (location.pathname.replace(/^\/|\.html$/g, '').replace(/\//g, '-') || 'inicio');
    const h = tabla.closest('section, .card');
    const titulo = h && h.querySelector('h2') ? h.querySelector('h2').textContent : 'tabla-' + (i + 1);
    const s = (base + '-' + titulo).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    return s.slice(0, 90) + '.csv';
  }
  function preparar() {
    document.querySelectorAll('table').forEach((tabla, i) => {
      if (tabla.dataset.descarga || tabla.rows.length < 2) return;
      const caja = tabla.closest('.tw, .tabla-scroll') || tabla;
      if (caja.nextElementSibling && caja.nextElementSibling.classList.contains('descargar')) return;
      tabla.dataset.descarga = '1';
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'btn mini descargar'; b.textContent = 'Descargar tabla (Excel/CSV)';
      b.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob(['﻿' + csv(tabla)], {type: 'text/csv;charset=utf-8'}));
        a.download = nombre(tabla, i); document.body.append(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(a.href), 4000);
        if (window.va) window.va('event', {name: 'descarga', data: {pagina: location.pathname}});
      });
      caja.after(b);
    });
  }
  const iniciar = () => { preparar(); new MutationObserver(() => { clearTimeout(iniciar.t); iniciar.t = setTimeout(preparar, 200); }).observe(document.body, {childList: true, subtree: true}); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
})();
