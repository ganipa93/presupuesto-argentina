// portada.js — se publica en /js/portada.js (lo copia scripts/build.py). Los datos llegan en window.CFG.
const DATA = window.CFG.DATA;
const $ = (s) => document.querySelector(s);
const nf0 = new Intl.NumberFormat('es-AR', {maximumFractionDigits: 0});
const nf1 = new Intl.NumberFormat('es-AR', {maximumFractionDigits: 1});
const nf2 = new Intl.NumberFormat('es-AR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const pct = (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + nf1.format(Math.abs(v)) + '%';
const C1 = 'var(--c1)', CRIT = 'var(--crit)', MUTED = 'var(--mutedbar)';
const S = (k) => DATA.supuestos.find((r) => r.clave === k);
const INFL = S('infl_prom').proyecto2027;
const realOf = (r, infl) => ((1 + r.var_pct / 100) / (1 + infl / 100) - 1) * 100;
const el = (tag, props, ...kids) => { const e = document.createElement(tag); Object.assign(e, props || {}); kids.forEach((k) => e.append(k)); return e; };

function hb(box, rows, o) {
  const vals = rows.map(o.value);
  const lo = Math.min(0, ...vals), hi = Math.max(0, ...vals, o.ref || 0), span = (hi - lo) || 1;
  box.replaceChildren(...rows.map((r, i) => {
    const v = vals[i];
    const track = el('span', {className: 'hb-t'});
    track.style.setProperty('--z', ((0 - lo) / span * 100) + '%');
    const bar = el('i');
    bar.style.left = ((Math.min(0, v) - lo) / span * 100) + '%';
    bar.style.width = (Math.abs(v) / span * 100) + '%';
    bar.style.background = o.color ? o.color(r, v) : (v < 0 ? CRIT : C1);
    track.append(bar);
    if (o.ref != null) { const m = el('b'); m.style.left = ((o.ref - lo) / span * 100) + '%'; track.append(m); }
    return el('div', {className: 'hb'}, el('span', {className: 'hb-l', textContent: o.label(r)}), track, el('span', {className: 'hb-v', textContent: o.fmt(v)}));
  }));
}
function fill(sel, rows, cols, rowCls) {
  const t = $(sel), key = t.dataset.rowKey;
  t.tBodies[0].replaceChildren(...rows.map((r) => {
    const tr = el('tr'); tr.dataset.key = r[key];
    if (rowCls && rowCls(r)) tr.className = rowCls(r);
    cols.forEach(([f, fm, cls]) => {
      const v = r[f];
      const td = el(f === cols[0][0] ? 'th' : 'td', {textContent: v == null ? '—' : (fm ? fm(v, r) : v)});
      if (f === cols[0][0]) td.scope = 'row';
      if (cls === 'pn') td.className = v == null ? '' : (v < 0 ? 'neg' : 'pos'); else if (cls) td.className = cls;
      tr.append(td);
    });
    return tr;
  }));
}
function cards(box, rows) {
  box.replaceChildren(...rows.map((r) => {
    const b = el('button', {type: 'button', className: 'btn mini', textContent: 'Imagen para compartir'});
    b.dataset.placaV = r.id;
    return el('div', {className: 'v'}, el('h3', {textContent: r.tema}), el('span', {className: 'pill ' + r.semaforo, textContent: r.estado}),
      el('p', {className: 'dato', textContent: r.dato}), el('p', {textContent: r.lectura}), b);
  }));
}
const fmt0 = (v) => nf0.format(v), fmt1 = (v) => nf1.format(v), bn = (v) => nf1.format(v / 1e6);
const REF = DATA.referencias, POB = REF.poblacion;
let UNIDAD = 'bn';
try { if (localStorage.getItem('unidad') === 'hab') UNIDAD = 'hab'; } catch (e) {}
/* v en millones de pesos */
function money(v, corto) {
  if (UNIDAD === 'hab') return '$' + nf0.format(v * 1e6 / POB / 12) + (corto ? '' : ' por mes');
  return nf1.format(v / 1e6) + (corto ? '' : ' bn');
}

function render() {
  const M = DATA.ministerios, F = DATA.funciones, V = DATA.veredictos;
  const a = M.reduce((s, r) => s + r.y2026, 0), b = M.reduce((s, r) => s + r.y2027, 0);
  $('#k-gasto').textContent = money(b, true);
  $('#h-total').replaceChildren('$' + nf1.format(b / 1e6) + ' ', el('small', {textContent: 'billones'}));
  $('#h-hab').replaceChildren('Son ', el('b', {textContent: '$' + nf0.format(b * 1e6 / POB / 12) + ' por mes'}), ' por cada habitante del país.');
  const ssh = DATA.funciones.find((x) => x.codigo === '3.3').y2027 / b * 100;
  $('#h-barra').style.width = ssh.toFixed(1) + '%';
  $('#h-ss').textContent = 'El ' + nf0.format(ssh) + '% va a jubilaciones, pensiones y asignaciones (seguridad social).';
  $('#k-gasto-lab').textContent = UNIDAD === 'hab' ? 'Gasto previsto para 2027, por habitante por mes' : 'Gasto previsto para 2027 (billones de $)';
  document.querySelectorAll('[data-unidad-nota]').forEach((n) => { n.textContent = UNIDAD === 'hab' ? 'Pesos por habitante por mes.' : 'Billones de pesos.'; });
  $('#k-var').textContent = pct((b / a - 1) * 100);
  $('#k-infl').textContent = nf1.format(S('inflacion').proyecto2027) + '%';
  $('#k-real').textContent = pct(((b / a) / (1 + INFL / 100) - 1) * 100);
  $('#claves').replaceChildren(...DATA.claves.map((c) => el('div', {className: 'clave'}, el('h3', {textContent: c.titulo}), el('p', {className: 'note', textContent: c.texto}))));
  $('#score').replaceChildren(...['2026', '2027'].map((p) => {
    const n = (s) => V.filter((r) => r.periodo === p && r.semaforo === s).length;
    return el('p', {textContent: p + ': ' + n('ok') + ' en verde, ' + n('warn') + ' en amarillo, ' + n('bad') + ' en rojo.'});
  }));
  hb($('#r-final'), F.filter((x) => x.nivel === 'finalidad').sort((x, y) => y.y2027 - x.y2027), {label: (x) => x.nombre, value: (x) => x.y2027, fmt: (v) => money(v)});
  hb($('#r-real'), F.filter((x) => x.nivel === 'función').map((x) => ({...x, real: realOf(x, INFL)})).sort((x, y) => y.real - x.real), {label: (x) => x.nombre, value: (x) => x.real, fmt: pct});
  renderPerfiles();
  hb($('#g-min'), [...M].sort((x, y) => y.y2027 - x.y2027), {label: (x) => x.jurisdiccion, value: (x) => x.y2027, fmt: (v) => money(v)});
  fill('#t-min', M, [['jurisdiccion'], ['y2026', fmt0], ['y2027', fmt0], ['var_pct', pct, 'pn']]);
  drawFun();
  fill('#t-fun', F, [['codigo'], ['nombre', null, 't'], ['y2026', fmt0], ['y2027', fmt0], ['var_pct', pct, 'pn']], (x) => x.nivel === 'finalidad' ? 'fin' : 'sub');
  hb($('#g-car'), DATA.caracter_total, {label: (x) => x.concepto, value: (x) => x.y2027, fmt: (v) => money(v)});
  fill('#t-carmin', DATA.caracter_ministerio, ['jurisdiccion', 'remuneraciones', 'bienes_servicios', 'intereses', 'prestaciones_ss', 'transf_corrientes', 'inversion_real', 'transf_capital', 'total'].map((f, i) => i === 0 ? [f] : [f, fmt0]));
  fill('#t-ben', DATA.beneficiarios, [['concepto'], ['tipo', null, 't'], ['y2026', fmt0], ['y2027', fmt0]]);
  hb($('#rc-chart'), [...DATA.recursos].sort((x, y) => y.y2027 - x.y2027), {label: (x) => x.concepto, value: (x) => x.y2027, fmt: (v) => money(v)});
  fill('#t-rec', DATA.recursos, [['concepto'], ['y2026', fmt0], ['y2027', fmt0], ['pib2026', (v) => nf2.format(v)], ['pib2027', (v) => nf2.format(v)]]);
  fill('#t-cpib', DATA.cuenta_pib, [['concepto'], ['pib2026', fmt1], ['pib2027', fmt1]]);
  hb($('#fu-chart'), DATA.fuentes_2027, {label: (x) => x.fuente, value: (x) => x.billones * 1e6, fmt: (v) => money(v)});
  hb($('#gt-chart'), DATA.gasto_tributario, {label: (x) => x.concepto, value: (x) => x.monto, fmt: (v) => money(v), color: (x) => x.concepto.startsWith('Total') ? MUTED : C1});
  const E = DATA.ejecucion;
  hb($('#ej-chart'), E.filter((x) => x.tipo !== 'resultado' && x.pct_ejec != null), {label: (x) => x.concepto, value: (x) => x.pct_ejec, fmt: (v) => nf1.format(v) + '%', ref: 7 / 12 * 100, color: (x, v) => v < 50 ? MUTED : C1});
  fill('#t-ej', E, [['concepto'], ['ejec2025', fmt0], ['estimado2026', fmt0], ['ejec2026', fmt0], ['var_pct', pct, 'pn'], ['pct_ejec', (v) => nf1.format(v) + '%']], (x) => x.tipo === 'total' ? 'fin' : '');
  hb($('#asap-chart'), DATA.asap, {label: (x) => x.concepto, value: (x) => x.var_real_pct, fmt: pct});
  fill('#t-sup', DATA.supuestos, [['variable'], ['unidad', null, 't'], ['ley2026', fmt1], ['estimado2026', fmt1], ['proyecto2027', fmt1]]);
  cards($('#v26'), V.filter((x) => x.periodo === '2026'));
  cards($('#v27'), V.filter((x) => x.periodo === '2027'));
  drawSim();
  const LV = DATA.ley_vs_proyecto.map((r) => ({concepto: r.concepto, var_pct: (r.proyecto2027 / r.ley2026 - 1) * 100}));
  hb($('#lv-chart'), LV, {label: (x) => x.concepto, value: (x) => x.var_pct, fmt: pct, color: () => C1});
  fill('#t-lvp', DATA.ley_vs_proyecto, [['concepto'], ['ley2026', fmt0], ['proyecto2027', fmt0], ['nota', null, 't']]);
  fill('#t-nor', DATA.normas, [['articulo'], ['tema', null, 't'], ['efecto', null, 't']]);
  calcular();
  marcarUnidad();
  renderCongreso();
  renderEjecMin();
}
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const fechaLarga = (iso) => { const [a, m, d] = iso.split('-').map(Number); return d + ' de ' + MESES[m - 1] + ' de ' + a; };
const ESTADO_CG = {hecho: 'Hecho', proximo: 'Próximo paso', pendiente: 'Pendiente'};
function fuenteLink(f) { return f ? el('a', {href: f.url, target: '_blank', rel: 'noopener', textContent: 'Fuente: ' + f.nombre}) : ''; }
function renderCongreso() {
  const C = DATA.congreso;
  $('#cg-act').textContent = 'Actualizado al ' + fechaLarga(C.actualizado) + '. Las fechas futuras son las que informan los bloques y pueden cambiar.';
  $('#cg-etapas').replaceChildren(...C.etapas.map((e) => el('li', {className: e.estado},
    el('span', {className: 'cg-fecha', textContent: e.fecha_texto + ' · ' + ESTADO_CG[e.estado]}),
    el('h3', {textContent: e.titulo}), el('p', {className: 'note', textContent: e.detalle}), fuenteLink(e.fuente))));
  $('#cg-cambios').replaceChildren(...C.cambios.map((c) => el('div', {className: 'v'},
    el('h3', {textContent: c.tema}), el('span', {className: 'pill warn', textContent: c.estado}),
    el('p', {className: 'dato', textContent: fechaLarga(c.fecha)}), el('p', {textContent: c.detalle}), fuenteLink(c.fuente))));
  const prox = C.etapas.find((e) => e.estado === 'proximo');
  const av = $('#cg-proximo');
  if (prox) {
    const a = el('a', {href: '/congreso', textContent: 'Ver el seguimiento'});
    av.replaceChildren(el('span', {className: 'lab', textContent: 'En el Congreso · ' + prox.fecha_texto}), el('span', {textContent: prox.titulo + '. '}), a);
    av.hidden = false;
  } else av.hidden = true;
}
function renderEjecMin() {
  const E = DATA.ejecucion_ministerios;
  if (!E || !E.filas || !E.filas.length) { $('#em-card').hidden = true; return; }
  $('#em-card').hidden = false;
  const mes = E.ultimo_mes_completo || E.ultimo_mes;
  const hasta = E.mes_parcial ? MESES[mes - 1] + ' completo y lo que va de ' + MESES[E.ultimo_mes - 1] : MESES[mes - 1];
  $('#em-nota').textContent = 'Gastado hasta ' + hasta + ' de ' + E.ejercicio + ' contra el crédito vigente (el presupuesto ya modificado durante el año). La línea punteada marca ' + mes + ' de 12 meses. Fuente: Presupuesto Abierto, actualizado automáticamente el ' + fechaLarga(E.actualizado) + '.';
  hb($('#em-chart'), [...E.filas].sort((x, y) => x.pct_ejecutado - y.pct_ejecutado), {label: (x) => x.jurisdiccion, value: (x) => x.pct_ejecutado, fmt: (v) => nf1.format(v) + '%', ref: mes / 12 * 100, color: (x, v) => v < mes / 12 * 100 * 0.85 ? MUTED : C1});
  fill('#t-em', E.filas, [['jurisdiccion'], ['credito_inicial', fmt0], ['credito_vigente', fmt0], ['devengado', fmt0], ['pct_ejecutado', (v) => nf1.format(v) + '%']]);
}

const TAG = {'+': ['A favor', 'mas'], '-': ['En contra', 'menos'], '~': ['A tener en cuenta', 'ojo']};
let perfilActual = null;
function renderPerfiles() {
  $('#perfiles').replaceChildren(...DATA.impacto.map((p) => {
    const b = el('button', {type: 'button', textContent: p.perfil});
    b.dataset.perfil = p.id;
    b.setAttribute('aria-pressed', String(p.id === perfilActual));
    b.addEventListener('click', () => { perfilActual = p.id; show('que-me-cambia', true); });
    return b;
  }));
  $('#perfil-detalle').replaceChildren(...DATA.impacto.map((p) => {
    const box = el('article', {className: 'card perfil', id: 'perfil-' + p.id});
    box.hidden = p.id !== perfilActual;
    box.append(el('h2', {textContent: p.perfil}),
      el('ul', {className: 'puntos'}, ...p.puntos.map((pt) => el('li', {}, el('span', {className: 'tag ' + TAG[pt.signo][1], textContent: TAG[pt.signo][0]}), el('span', {textContent: pt.texto})))));
    const bp = el('button', {type: 'button', className: 'btn primary', textContent: 'Crear imagen de este caso para compartir'});
    bp.dataset.placaP = p.id;
    box.append(el('div', {className: 'share'}, bp));
    return box;
  }));
}
function drawFun() {
  const m = $('#metric').value;
  const rows = DATA.funciones.filter((x) => x.nivel === 'función').map((x) => ({...x, real: realOf(x, INFL)})).sort((x, y) => y[m] - x[m]);
  hb($('#g-fun'), rows, {label: (x) => x.nombre, value: (x) => x[m], fmt: (v) => m === 'y2027' ? money(v) : pct(v), color: (x, v) => m === 'y2027' || v >= 0 ? C1 : CRIT});
}
function drawSim() {
  const infl = Number($('#s-inf').value), usd = Number($('#s-usd').value);
  $('#o-inf').textContent = nf1.format(infl) + '%';
  $('#o-usd').textContent = '+' + nf0.format(usd) + '%';
  const ss = DATA.funciones.find((x) => x.codigo === '3.3').y2027 / 1e6;
  const extra = ss * ((1 + infl / 100) / (1 + INFL / 100) - 1);
  const intr = S('costo_usd10').proyecto2027 * usd / 10;
  $('#r-ss').textContent = (extra < 0 ? 'sobran ' : '') + nf1.format(Math.abs(extra));
  $('#r-int').textContent = nf1.format(intr);
  $('#r-pct').textContent = nf0.format(Math.max(0, extra + intr) / S('superavit').proyecto2027 * 100) + '%';
  hb($('#sim-chart'), DATA.funciones.filter((x) => x.nivel === 'función').map((x) => ({...x, real: realOf(x, infl)})).sort((x, y) => y.real - x.real), {label: (x) => x.nombre, value: (x) => x.real, fmt: pct});
}

/* Navegación: cada sección tiene su dirección propia (/impuestos, /que-me-cambia/jubilados, …) */
const SITE = window.CFG.SITE;
const SECCIONES = window.CFG.SECCIONES;
const PERFILES_SEO = window.CFG.PERFILES;
const TABS = Object.keys(SECCIONES);
let tabActual = 'resumen';
function rutaActual() { return tabActual === 'que-me-cambia' && perfilActual ? '/que-me-cambia/' + perfilActual : SECCIONES[tabActual].ruta; }
function metaActual() {
  const m = {...SECCIONES[tabActual]};
  if (tabActual === 'que-me-cambia' && perfilActual && PERFILES_SEO[perfilActual]) Object.assign(m, PERFILES_SEO[perfilActual]);
  return m;
}
const norm2 = (t) => t.normalize('NFD').replace(/[\u0300-\u036f¿?]/g, '').toLowerCase().trim();
function setMeta(sel, attr, val) { const n = document.querySelector(sel); if (n) n.setAttribute(attr, val); }
function show(tab, push) {
  tabActual = tab;
  const m = metaActual(), url = SITE + rutaActual();
  document.querySelectorAll('[data-panel]').forEach((s) => { s.hidden = s.dataset.panel !== tab; });
  document.querySelectorAll('#perfiles button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.perfil === perfilActual)));
  document.querySelectorAll('#perfil-detalle .perfil').forEach((a) => { a.hidden = a.id !== 'perfil-' + perfilActual; });
  document.querySelectorAll('.secnav a[data-tab]').forEach((a) => { if (a.dataset.tab === tab) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  const inicio = tab === 'resumen';
  ['#hero-busca', '#hero-chips', '#hero-cifra'].forEach((s) => { $(s).hidden = !inicio; });
  $('#hero').style.gridTemplateColumns = inicio ? '' : '1fr';
  $('#titulo').textContent = m.h1; $('#bajada').textContent = m.bajada;
  // en las secciones, el primer título de la tarjeta repite el título de la página: se oculta (sigue para lectores de pantalla)
  document.querySelectorAll('[data-panel] > .card:first-child > h2').forEach((h) => h.classList.toggle('vh', !inicio && h.closest('[data-panel]').dataset.panel === tab && norm2(h.textContent) === norm2(m.h1)));
  document.title = m.titulo;
  setMeta('meta[name="description"]', 'content', m.descripcion);
  setMeta('link[rel="canonical"]', 'href', url);
  setMeta('meta[property="og:url"]', 'content', url);
  setMeta('meta[property="og:title"]', 'content', m.titulo);
  setMeta('meta[property="og:description"]', 'content', m.descripcion);
  setMeta('meta[name="twitter:title"]', 'content', m.titulo);
  setMeta('meta[name="twitter:description"]', 'content', m.descripcion);
  if (push && location.pathname !== rutaActual()) { try { history.pushState(null, '', rutaActual()); } catch (e) {} }
  const txt = m.compartir || m.titulo;
  $('#sh-wa').href = 'https://wa.me/?text=' + encodeURIComponent(txt + ' ' + url);
  $('#sh-x').href = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(txt) + '&url=' + encodeURIComponent(url);
  const act = document.querySelector('.secnav a[aria-current]'); if (act && act.scrollIntoView && push) act.scrollIntoView({block: 'nearest', inline: 'center'});
  if (window.va && push) window.va('event', {name: 'seccion', data: {seccion: rutaActual()}});
}
function tabDeRuta(path) {
  path = path.replace(/\.html$/, '').replace(/\/+$/, '') || '/';
  const pm = path.match(/^\/que-me-cambia\/([a-z-]+)$/);
  if (pm && DATA.impacto.some((p) => p.id === pm[1])) return ['que-me-cambia', pm[1]];
  const t = TABS.find((k) => SECCIONES[k].ruta === path);
  return t ? [t, null] : null;
}
function route() {
  // links viejos con # (#impuestos, #que-me-cambia-jubilados) siguen andando
  const h = decodeURIComponent(location.hash.slice(1));
  if (h) {
    const viejo = h === 'tus-impuestos' ? ['tus-impuestos', null] : h.startsWith('que-me-cambia-') ? ['que-me-cambia', h.slice(14)] : TABS.includes(h) ? [h, null] : null;
    if (viejo) { if (viejo[1]) perfilActual = viejo[1]; show(viejo[0], false); try { history.replaceState(null, '', rutaActual()); } catch (e) {} return; }
  }
  const r = tabDeRuta(location.pathname) || ['resumen', null];
  perfilActual = r[1] || (r[0] === 'que-me-cambia' ? null : perfilActual);
  if (r[0] === 'que-me-cambia' && !perfilActual) perfilActual = null;
  show(r[0], false);
}
document.addEventListener('click', (e) => {
  if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
  const a = e.target.closest('a[href]'); if (!a || a.target === '_blank') return;
  const u = new URL(a.href, location.href); if (u.origin !== location.origin || u.search) return;
  const r = tabDeRuta(u.pathname); if (!r) return;
  e.preventDefault();
  if (r[1]) perfilActual = r[1];
  show(r[0], true);
  const nav = $('.secnav'); if (nav.getBoundingClientRect().top < 0 || a.closest('main, section')) window.scrollTo({top: Math.max(0, nav.offsetTop - 4), behavior: 'smooth'});
});
window.addEventListener('popstate', route);
function toast(msg) { const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2200); }
$('#sh-copy').addEventListener('click', async () => {
  const url = SITE + rutaActual(); $('#share').open = false;
  try { await navigator.clipboard.writeText(url); toast('Link copiado'); } catch (e) { prompt('Copiá el link:', url); }
});
if (navigator.share) {
  $('#sh-native').hidden = false;
  $('#sh-native').addEventListener('click', () => { $('#share').open = false; navigator.share({title: document.title, text: metaActual().compartir || document.title, url: SITE + rutaActual()}).catch(() => {}); });
}
$('#s-inf').addEventListener('input', drawSim);
$('#s-usd').addEventListener('input', drawSim);
$('#metric').addEventListener('change', drawFun);
/* Selector de unidades */
function marcarUnidad() { document.querySelectorAll('[data-unidad]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.unidad === UNIDAD))); }
document.querySelectorAll('[data-unidad]').forEach((b) => b.addEventListener('click', () => {
  UNIDAD = b.dataset.unidad;
  try { localStorage.setItem('unidad', UNIDAD); } catch (e) {}
  render(); show(tabActual, false);
  if (window.va) window.va('event', {name: 'unidad', data: {unidad: UNIDAD}});
}));

/* Calculadora: ¿a dónde van tus impuestos? */
let ULTIMO = null;
const pesos = (v) => '$' + nf0.format(Math.round(v));
function calcular() {
  const n = (id) => Math.max(0, Number($(id).value) || 0);
  const sueldo = n('#c-sueldo'), gasto = n('#c-gasto'), gan = n('#c-gan'), mono = n('#c-mono');
  const total = sueldo * REF.aportes_pct / 100 + gasto * REF.iva_efectivo_pct / 100 + gan + mono;
  const [nac, prov, otros] = REF.reparto.map((r) => total * r.pct / 100);
  const F = DATA.funciones;
  const totalGasto = F.filter((x) => x.nivel === 'finalidad').reduce((s, x) => s + x.y2027, 0);
  const areas = F.filter((x) => x.nivel === 'función' || x.codigo === '5')
    .map((x) => ({nombre: x.codigo === '5' ? 'Intereses de la deuda' : x.nombre, monto: nac * x.y2027 / totalGasto, codigo: x.codigo}))
    .sort((a, b) => b.monto - a.monto);
  const top = areas.slice(0, 8), resto = areas.slice(8).reduce((s, x) => s + x.monto, 0);
  const filas = [{nombre: REF.reparto[1].destino, monto: prov, tipo: 'fuera'}, {nombre: REF.reparto[2].destino, monto: otros, tipo: 'fuera'},
    ...top.map((x) => ({nombre: 'Nación: ' + x.nombre.charAt(0).toLowerCase() + x.nombre.slice(1), monto: x.monto})), {nombre: 'Nación: resto de las áreas', monto: resto}];
  hb($('#c-reparto'), filas, {label: (x) => x.nombre, value: (x) => x.monto, fmt: pesos, color: (x) => x.tipo === 'fuera' ? MUTED : C1});
  const ss = (areas.find((x) => x.codigo === '3.3') || {monto: 0}).monto;
  $('#c-total').textContent = pesos(total);
  $('#c-dias').textContent = sueldo > 0 ? nf1.format(total / sueldo * 30) + ' días de sueldo' : '—';
  $('#c-ss').textContent = pesos(ss);
  ULTIMO = {total, filas};
}
['#c-sueldo', '#c-gasto', '#c-gan', '#c-mono'].forEach((id) => $(id).addEventListener('input', calcular));

/* Placas para compartir en redes */
const PL = {w: 1080, h: 1350, m: 84, bg: '#13294b', fg: '#ffffff', muted: '#c9d6e6', acc: '#f2b632', ok: '#7ddc9a', warn: '#f2c26b', bad: '#ff9b8f'};
const SERIF = '"Source Serif 4", Georgia, serif', SANS = '"Source Sans 3", system-ui, sans-serif';
function lineas(ctx, texto, ancho) {
  const out = []; let l = '';
  for (const w of String(texto).split(/\s+/)) { const t = l ? l + ' ' + w : w; if (ctx.measureText(t).width > ancho && l) { out.push(l); l = w; } else l = t; }
  if (l) out.push(l); return out;
}
async function placa(o) {
  try { await Promise.all([document.fonts.load('400 60px "Source Serif 4"'), document.fonts.load('600 30px "Source Sans 3"'), document.fonts.load('400 30px "Source Sans 3"')]); } catch (e) {}
  const c = document.createElement('canvas'); c.width = PL.w; c.height = PL.h;
  const ctx = c.getContext('2d'), W = PL.w - PL.m * 2;
  const pie = 150;
  const dibujar = (esc, off) => {
    ctx.fillStyle = PL.bg; ctx.fillRect(0, 0, PL.w, PL.h);
    let y = PL.m + 10 + off;
    ctx.textBaseline = 'top';
    ctx.fillStyle = PL.acc; ctx.font = '600 28px ' + SANS;
    ctx.fillText(o.kicker.toUpperCase(), PL.m, y); y += 64;
    const tf = Math.round(66 * esc); ctx.font = '400 ' + tf + 'px ' + SERIF; ctx.fillStyle = PL.fg;
    for (const l of lineas(ctx, o.titulo, W)) { ctx.fillText(l, PL.m, y); y += tf * 1.15; }
    y += 18 * esc;
    if (o.estado) {
      ctx.font = '600 ' + Math.round(30 * esc) + 'px ' + SANS;
      const pw = ctx.measureText(o.estado).width + 40, ph = Math.round(50 * esc);
      ctx.strokeStyle = PL[o.color] || PL.acc; ctx.lineWidth = 3; ctx.beginPath(); if (ctx.roundRect) ctx.roundRect(PL.m, y, pw, ph, ph / 2); else ctx.rect(PL.m, y, pw, ph); ctx.stroke();
      ctx.fillStyle = PL[o.color] || PL.acc; ctx.fillText(o.estado, PL.m + 20, y + (ph - 30 * esc) / 2); y += ph + 30 * esc;
    }
    for (const b of o.bloques) {
      if (b.tag) { ctx.font = '600 ' + Math.round(26 * esc) + 'px ' + SANS; ctx.fillStyle = PL[b.color] || PL.acc; ctx.fillText(b.tag.toUpperCase(), PL.m, y); y += 38 * esc; }
      const f = Math.round((b.grande ? 40 : 32) * esc); ctx.font = (b.fuerte ? '600 ' : '400 ') + f + 'px ' + SANS; ctx.fillStyle = b.tenue ? PL.muted : PL.fg;
      for (const l of lineas(ctx, b.texto, W - (b.valor ? 220 : 0))) { ctx.fillText(l, PL.m, y); y += f * 1.32; }
      if (b.valor) { ctx.font = '600 ' + f + 'px ' + SANS; ctx.fillStyle = PL.fg; ctx.textAlign = 'right'; ctx.fillText(b.valor, PL.w - PL.m, y - f * 1.32); ctx.textAlign = 'left'; }
      y += (b.sep == null ? 26 : b.sep) * esc;
    }
    return y - off;
  };
  let esc = 1, alto = dibujar(1, 0);
  while (alto > PL.h - pie && esc > 0.55) { esc -= 0.05; alto = dibujar(esc, 0); }
  const libre = PL.h - pie - alto;
  if (libre > 60) dibujar(esc, libre * 0.4);
  ctx.fillStyle = '#f2b632'; ctx.fillRect(PL.m, PL.h - pie + 20, W, 3);
  ctx.font = '600 30px ' + SANS; ctx.fillStyle = PL.fg; ctx.textBaseline = 'top';
  ctx.fillText(SITE.replace('https://', ''), PL.m, PL.h - pie + 48);
  ctx.font = '400 24px ' + SANS; ctx.fillStyle = PL.muted;
  ctx.fillText(o.fuente || 'Fuentes: Proyecto de Presupuesto 2027, Ley 27.798, INDEC, BCRA, FMI y ASAP', PL.m, PL.h - pie + 92);
  return c;
}
async function compartirPlaca(o, nombre) {
  const c = await placa(o);
  const blob = await new Promise((r) => c.toBlob(r, 'image/png'));
  const file = new File([blob], nombre + '.png', {type: 'image/png'});
  if (window.va) window.va('event', {name: 'placa', data: {placa: nombre}});
  if (navigator.canShare && navigator.canShare({files: [file]})) {
    try { await navigator.share({files: [file], text: o.titulo + ' ' + SITE}); return; } catch (e) { if (e.name === 'AbortError') return; }
  }
  const a = el('a', {href: URL.createObjectURL(blob), download: nombre + '.png'});
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  toast('Imagen descargada');
}
const COLOR_TAG = {'+': 'ok', '-': 'bad', '~': 'warn'};
document.addEventListener('click', (e) => {
  const bv = e.target.closest('[data-placa-v]'), bp = e.target.closest('[data-placa-p]');
  if (bv) {
    const v = DATA.veredictos.find((x) => x.id === bv.dataset.placaV);
    compartirPlaca({kicker: v.periodo === '2026' ? 'Presupuesto 2026: ¿se cumplió?' : 'Presupuesto 2027: ¿se cumplirá?', titulo: v.tema, estado: v.estado, color: v.semaforo,
      bloques: [{texto: v.dato, tenue: true}, {texto: v.lectura, grande: true}]}, 'presupuesto-' + v.periodo + '-' + v.id);
  }
  if (bp) {
    const p = DATA.impacto.find((x) => x.id === bp.dataset.placaP);
    compartirPlaca({kicker: '¿Qué te cambia el Presupuesto 2027?', titulo: p.perfil,
      bloques: p.puntos.map((pt) => ({tag: TAG[pt.signo][0], color: COLOR_TAG[pt.signo], texto: pt.texto}))}, 'presupuesto-2027-' + p.id);
  }
});
$('#c-placa').addEventListener('click', () => {
  if (!ULTIMO) return;
  compartirPlaca({kicker: '¿A dónde van mis impuestos?', titulo: 'Pago unos ' + pesos(ULTIMO.total) + ' por mes en impuestos y aportes nacionales',
    bloques: ULTIMO.filas.slice(0, 8).map((f) => ({texto: f.nombre, valor: pesos(f.monto), sep: 8})),
    fuente: 'Estimación según el Presupuesto 2027. Calculá la tuya en el sitio.'}, 'mis-impuestos-2027');
});
render();
route();
