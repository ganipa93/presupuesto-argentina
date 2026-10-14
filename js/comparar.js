// comparar.js — comparador de programas, organismos y provincias (/comparar?c=a,b,c).
// Los datos salen de /datos/comparar.json, que arma scripts/paginas.py.
(function () {
  const $ = (s) => document.querySelector(s);
  const COLORES = ['var(--c1)', 'var(--acc)', 'var(--ok)'];
  const NOMBRES_COLOR = ['azul', 'amarillo', 'verde'];
  const TIPO = {p: 'Programa', e: 'Presupuesto propio', v: 'Provincia'};
  const norm = (s) => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const nf = (d) => new Intl.NumberFormat('es-AR', {maximumFractionDigits: d, minimumFractionDigits: d});
  const el = (tag, attrs, ...hijos) => { const e = document.createElement(tag); for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') e.className = v; else if (k === 'text') e.textContent = v; else if (k === 'html') e.innerHTML = v; else e.setAttribute(k, v); } e.append(...hijos.filter((h) => h != null)); return e; };
  function plata(m) {
    if (m == null) return '—';
    const a = Math.abs(m);
    if (a >= 1e6) return '$' + nf(2).format(m / 1e6) + ' billones';
    if (a >= 1000) return '$' + nf(0).format(m) + ' millones';
    if (a >= 1) return '$' + nf(1).format(m) + ' millones';
    return '$' + nf(0).format(m * 1e6);
  }
  const TC = window.CMP_TC || {};
  function usd(m, anio) {
    if (m == null || !m || !TC[anio]) return null;
    const u = m / TC[anio], a = Math.abs(u);
    if (a >= 100) return 'US$ ' + nf(0).format(u) + ' millones';
    if (a >= 1) return 'US$ ' + nf(1).format(u) + ' millones';
    return 'US$ ' + nf(0).format(u * 1e6);
  }
  const celdaN = (m, anio) => { if (m == null) return '—'; const u = anio && usd(m, anio); return el('span', {}, el('span', {'data-n': String(Math.round(m * 10) / 10)}, plata(m)), u ? el('small', {class: 'usd', style: 'display:block', text: '≈ ' + u}) : null); };
  let D = null, porId = {}, elegidos = [null, null, null];

  function anunciar(t) { const a = $('#cmp-anuncio'); if (a) { a.textContent = ''; setTimeout(() => { a.textContent = t; }, 50); } }

  function slots() {
    const box = $('#slots');
    box.replaceChildren(...[0, 1, 2].map((i) => {
      const it = elegidos[i] && porId[elegidos[i]];
      const input = el('input', {type: 'search', id: 'slot' + i, placeholder: i === 0 ? 'Ej.: universidades, Córdoba, INCAA' : 'Agregar otro (opcional)', autocomplete: 'off', value: it ? it.n : '', role: 'combobox', 'aria-autocomplete': 'list', 'aria-expanded': 'false', 'aria-controls': 'lista' + i});
      const lista = el('ul', {role: 'listbox', id: 'lista' + i, 'aria-label': 'Sugerencias para el ' + (i + 1) + '.º elemento'}); lista.hidden = true;
      const label = el('label', {for: 'slot' + i}, el('i', {style: 'background:' + COLORES[i]}), (i + 1) + '.º (' + NOMBRES_COLOR[i] + ')');
      let activo = -1;
      const opciones = () => [...lista.children];
      const marcar = (k) => {
        const ops = opciones(); activo = ops.length ? (k + ops.length) % ops.length : -1;
        ops.forEach((o, j) => o.setAttribute('aria-selected', j === activo ? 'true' : 'false'));
        if (activo >= 0) { input.setAttribute('aria-activedescendant', ops[activo].id); ops[activo].scrollIntoView({block: 'nearest'}); } else input.removeAttribute('aria-activedescendant');
      };
      const cerrar = () => { lista.hidden = true; activo = -1; input.setAttribute('aria-expanded', 'false'); input.removeAttribute('aria-activedescendant'); };
      const elegir = (x) => { elegidos[i] = x.id; cerrar(); actualizar(); };
      const sugerir = () => {
        const q = norm(input.value).trim();
        if (q.length < 2) { cerrar(); return; }
        const ps = q.split(/\s+/);
        const hall = D.items.filter((x) => { const t = norm(x.n + ' ' + x.o); return ps.every((p) => t.includes(p)); })
          .sort((a, b) => (b.t === 'v') - (a.t === 'v') || ((b.a27 || b.g27 || b.v26 || 0) - (a.a27 || a.g27 || a.v26 || 0))).slice(0, 10);
        lista.replaceChildren(...hall.map((x, j) => {
          const li = el('li', {role: 'option', id: 'opc' + i + '-' + j, 'aria-selected': 'false'}, x.n, el('small', {text: TIPO[x.t] + ' · ' + x.o}));
          li.addEventListener('mousedown', (ev) => ev.preventDefault());
          li.addEventListener('click', () => elegir(x));
          li._x = x;
          return li;
        }));
        activo = -1; input.removeAttribute('aria-activedescendant');
        lista.hidden = !hall.length;
        input.setAttribute('aria-expanded', hall.length ? 'true' : 'false');
        if (hall.length) anunciar(hall.length + (hall.length === 1 ? ' sugerencia' : ' sugerencias') + '. Usá las flechas para recorrerlas.');
      };
      input.addEventListener('input', sugerir);
      input.addEventListener('focus', sugerir);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') { cerrar(); return; }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          if (lista.hidden) sugerir();
          if (lista.hidden) return;
          e.preventDefault(); marcar(activo < 0 ? (e.key === 'ArrowDown' ? 0 : -1) : activo + (e.key === 'ArrowDown' ? 1 : -1)); return;
        }
        if (e.key === 'Enter' && !lista.hidden) { const o = opciones()[activo >= 0 ? activo : 0]; if (o) { e.preventDefault(); elegir(o._x); } }
      });
      input.addEventListener('blur', () => setTimeout(cerrar, 200));
      const quitar = it ? el('button', {type: 'button', class: 'btn mini', text: 'Quitar'}) : null;
      if (quitar) quitar.addEventListener('click', () => { elegidos[i] = null; actualizar(); });
      return el('div', {class: 'slot'}, label, input, lista, quitar);
    }));
  }

  function grafico(sel) {
    const series = sel.map((x, i) => ({x, i, r: (x.r || []).filter((p) => p[1] > 0)})).filter((s) => s.r.length >= 3);
    if (!series.length) return null;
    const anios = [...new Set(series.flatMap((s) => s.r.map((p) => p[0])))].sort();
    const W = 640, H = 260, L = 70, R = 16, T = 16, B = 34;
    const mx = Math.max(...series.flatMap((s) => s.r.map((p) => p[1]))) * 1.08;
    const X = (a) => L + (anios.indexOf(a)) * (W - L - R) / Math.max(1, anios.length - 1);
    const Y = (v) => T + (1 - v / mx) * (H - T - B);
    const svg = ['<svg viewBox="0 0 ' + W + ' ' + H + '" width="100%" style="max-width:760px;color:var(--fg)" role="img" aria-label="Evolución en pesos de 2026">'];
    for (let k = 0; k <= 4; k++) { const v = mx * k / 4, y = Y(v); svg.push('<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y + '" y2="' + y + '" stroke="var(--line)"/><text x="' + (L - 6) + '" y="' + (y + 4) + '" text-anchor="end" font-size="11" fill="currentColor" opacity=".7">' + plata(v).replace(' millones', ' M').replace(' billones', ' bn') + '</text>'); }
    anios.forEach((a) => svg.push('<text x="' + X(a) + '" y="' + (H - 10) + '" text-anchor="middle" font-size="12" fill="currentColor" opacity=".75">' + a + '</text>'));
    series.forEach((s) => {
      const pts = s.r.map((p) => X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join(' ');
      svg.push('<polyline points="' + pts + '" fill="none" stroke="' + COLORES[s.i] + '" stroke-width="3" stroke-linejoin="round"/>');
      s.r.forEach((p) => svg.push('<circle cx="' + X(p[0]).toFixed(1) + '" cy="' + Y(p[1]).toFixed(1) + '" r="' + (p[2] === 'g' ? 4 : 5) + '" fill="' + (p[2] === 'g' ? COLORES[s.i] : 'var(--card)') + '" stroke="' + COLORES[s.i] + '" stroke-width="2"><title>' + s.x.n + ', ' + p[0] + ': ' + plata(p[1]) + ' (pesos de 2026)</title></circle>'));
    });
    svg.push('</svg>');
    return el('figure', {style: 'margin:0'}, el('div', {html: svg.join('')}), el('figcaption', {class: 'note', text: 'En pesos de 2026, descontada la inflación. Punto lleno: gastado; punto vacío: 2026 autorizado y 2027 pedido.' + (series.some((s) => s.x.so) ? ' Algunas líneas muestran el organismo entero porque el programa cambió de nombre.' : '')}));
  }

  function cambioReal(x) {
    const r = Object.fromEntries((x.r || []).map((p) => [p[0], p[1]]));
    const fin = r[2027] != null ? 2027 : r[2026] != null ? 2026 : null;
    if (!fin || !r[2023]) return '—';
    const c = (r[fin] / r[2023] - 1) * 100;
    return (c >= 0 ? '+' : '−') + nf(0).format(Math.abs(c)) + '% (2023→' + fin + ')';
  }

  function resultado() {
    const sel = elegidos.map((id, i) => (id && porId[id] ? {...porId[id], i} : null)).filter(Boolean);
    const box = $('#cmp-res');
    if (!sel.length) { box.replaceChildren(); return; }
    const filas = [
      ['Qué es', (x) => TIPO[x.t] + (x.t === 'v' ? '' : ' · ' + x.o)],
      ['Pedido para 2027', (x) => celdaN(x.t === 'e' ? x.g27 : x.a27, 2027)],
      ['2026: aprobado por ley', (x) => celdaN(x.t === 'e' ? x.g26 : x.l26, 2026)],
      ['2026: autorizado hoy', (x) => celdaN(x.v26, 2026)],
      ['2026: gastado', (x) => (x.d26 == null ? '—' : el('span', {}, celdaN(x.d26, 2026), x.v26 ? nf(0).format(x.d26 / x.v26 * 100) + '% de lo autorizado' : ''))],
      ['Cambio real desde 2023', (x) => cambioReal(x)],
      ['Por habitante (2026)', (x) => (x.hab ? el('span', {}, '$' + nf(0).format(x.hab), TC[2026] ? el('small', {class: 'usd', style: 'display:block', text: '≈ US$ ' + nf(0).format(x.hab / TC[2026])}) : null) : '—')],
      ['Página', (x) => (x.t === 'v' ? el('a', {href: '/provincias/' + x.id.replace('provincia-', ''), text: 'Ver la provincia'}) : el('a', {href: '/gasto/' + x.id, text: 'Ver el detalle'}))],
    ];
    const tabla = el('table', {class: 'cmp-tabla'},
      el('thead', {}, el('tr', {}, el('th', {scope: 'col', class: 't', text: ''}), ...sel.map((x) => el('th', {scope: 'col'}, el('i', {style: 'background:' + COLORES[x.i]}), x.n)))),
      el('tbody', {}, ...filas.map(([k, f]) => el('tr', {}, el('th', {scope: 'row', text: k}), ...sel.map((x) => { const v = f(x); return el('td', {}, typeof v === 'string' ? v : v); })))));
    const link = el('button', {type: 'button', class: 'btn', text: 'Copiar link a esta comparación'});
    link.addEventListener('click', async () => { const u = window.CMP_SITE + '/comparar?c=' + sel.map((x) => x.id).join(','); try { await navigator.clipboard.writeText(u); link.textContent = 'Link copiado'; } catch (e) { prompt('Copiá el link:', u); } });
    const g = grafico(sel);
    box.replaceChildren(el('section', {class: 'card'}, el('h2', {text: sel.map((x) => x.n).join(' vs. ')}), el('div', {class: 'tw'}, tabla), g, el('div', {}, link)));
    document.title = sel.map((x) => x.n).join(' vs. ') + ' · Comparador del presupuesto';
    anunciar('Comparando ' + sel.map((x) => x.n).join(' y ') + '.');
  }

  function actualizar() {
    try { const u = new URL(location.href); const ids = elegidos.filter(Boolean); if (ids.length) u.searchParams.set('c', ids.join(',')); else u.searchParams.delete('c'); history.replaceState(null, '', u); } catch (e) {}
    slots(); resultado();
    if (window.va && elegidos.some(Boolean)) window.va('event', {name: 'comparar', data: {c: elegidos.filter(Boolean).join(',').slice(0, 100)}});
  }

  fetch('/datos/comparar.json').then((r) => r.json()).then((d) => {
    D = d; d.items.forEach((x) => { porId[x.id] = x; });
    const c = new URL(location.href).searchParams.get('c');
    if (c) c.split(',').slice(0, 3).forEach((id, i) => { if (porId[id]) elegidos[i] = id; });
    slots(); resultado();
  }).catch(() => { $('#slots').textContent = 'No se pudieron cargar los datos. Recargá la página.'; });
})();
