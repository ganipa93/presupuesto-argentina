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
  document.addEventListener('click', async (ev) => {
    const b = ev.target.closest('[data-copiar]'); if (!b) return;
    const t = document.getElementById(b.dataset.copiar);
    const ok = b.dataset.ok || 'Código copiado';
    try { await navigator.clipboard.writeText(t.value); b.textContent = ok; } catch (e) { t.select(); document.execCommand('copy'); b.textContent = ok; }
    if (window.va) window.va('event', {name: b.dataset.evento || 'insertar', data: {pagina: location.pathname}});
  });
  // Accesibilidad: una tabla que se desplaza (a lo ancho o a lo alto) tiene que poder recorrerse con el
  // teclado. Se la marca como región con nombre y foco solo si de verdad desplaza, para no sumar paradas de Tab.
  const desplazable = (c) => c.scrollWidth > c.clientWidth + 1 || c.scrollHeight > c.clientHeight + 1;
  function regiones() {
    document.querySelectorAll('.tw, .tabla-scroll').forEach((caja) => {
      const tabla = caja.querySelector('table'); if (!tabla) return;
      if (!desplazable(caja)) {
        if (caja.dataset.region) { caja.removeAttribute('role'); caja.removeAttribute('aria-label'); caja.removeAttribute('tabindex'); delete caja.dataset.region; }
        return;
      }
      if (caja.dataset.region) return;
      const cap = tabla.caption && tabla.caption.textContent.trim();
      const bloque = caja.closest('section, .card');
      const h = bloque && bloque.querySelector('h2, h3');
      caja.dataset.region = '1';
      caja.setAttribute('role', 'region');
      caja.setAttribute('aria-label', 'Tabla: ' + (cap || (h && h.textContent.trim()) || 'datos'));
      caja.tabIndex = 0;
    });
  }
  const iniciar = () => {
    const todo = () => { preparar(); regiones(); };
    todo();
    new MutationObserver(() => { clearTimeout(iniciar.t); iniciar.t = setTimeout(todo, 200); }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['hidden']});
    window.addEventListener('resize', () => { clearTimeout(iniciar.r); iniciar.r = setTimeout(regiones, 200); });
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
})();
