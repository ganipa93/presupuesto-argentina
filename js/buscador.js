// buscador.js — se publica en /js/buscador.js (lo copia scripts/build.py). Los datos llegan en window.CFG.
const SITE = window.CFG.SITE;
const $ = (s) => document.querySelector(s);
const el = (tag, attrs, ...hijos) => { const e = document.createElement(tag); for (const [k, v] of Object.entries(attrs || {})) { if (k === 'class') e.className = v; else if (k === 'text') e.textContent = v; else e.setAttribute(k, v); } e.append(...hijos.filter((h) => h != null)); return e; };
const norm = (s) => ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
const nf = (d) => new Intl.NumberFormat('es-AR', {maximumFractionDigits: d, minimumFractionDigits: d});
function plata(m) {
  if (m == null) return '—';
  const a = Math.abs(m);
  if (a >= 1e6) return '$ ' + nf(2).format(m / 1e6) + ' billones';
  if (a >= 1000) return '$ ' + nf(0).format(m) + ' millones';
  if (a >= 1) return '$ ' + nf(1).format(m) + ' millones';
  if (a > 0) return '$ ' + nf(0).format(m * 1e6) + '';
  return '$ 0';
}
// Dólares al oficial promedio de cada año (BCRA); 2027, el que proyecta el Ministerio de Economía
const TC = window.CFG.TC || {};
function usd(m, anio) {
  if (m == null || !m || !TC[anio]) return null;
  const u = m / TC[anio], a = Math.abs(u);
  if (a >= 100) return 'US$ ' + nf(0).format(u) + ' millones';
  if (a >= 1) return 'US$ ' + nf(1).format(u) + ' millones';
  return 'US$ ' + nf(0).format(u * 1e6);
}
const pct = (a, b) => (b ? nf(0).format(a / b * 100) + '%' : '—');
function toast(m) { const t = $('#toast'); t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2000); }

// Sinónimos: lo que la gente escribe → cómo aparece en el presupuesto
const SINONIMOS = {
  cine: ['cine', 'cinemat', 'incaa'], peliculas: ['cinemat', 'incaa'], incaa: ['incaa', 'cinemat'],
  ruta: ['ruta', 'vialidad', 'vial', 'corredores viales'], vialidad: ['vialidad', 'vial'],
  tren: ['tren', 'ferrocarril', 'ferroviari'], ferrocarril: ['ferrocarril', 'ferroviari', 'tren'],
  universidad: ['universidad', 'universitari', 'educacion superior'], facultad: ['universidad', 'universitari'],
  pami: ['pami', 'inssjp', 'jubilados y pensionados'],
  jubilacion: ['prestaciones previsionales', 'jubilac', 'previsional'], jubilado: ['prestaciones previsionales', 'jubilad', 'pami'],
  asignacion: ['asignaciones familiares', 'asignacion universal', 'asignacion'], auh: ['asignaciones familiares', 'asignacion universal'],
  hospital: ['hospital', 'atencion medica', 'sanitari'], salud: ['salud', 'hospital', 'sanitari', 'medic'],
  discapacidad: ['discapacidad', 'invalidez'],
  ciencia: ['ciencia', 'conicet', 'cientific', 'investigacion'], conicet: ['conicet'],
  seguridad: ['seguridad', 'gendarmeria', 'prefectura', 'policia', 'aeroportuaria'], policia: ['policia'],
  energia: ['energ', 'electric', 'enarsa', 'combustible', ' gas '], subsidio: ['subsidio', 'asistencia financiera'], luz: ['electric', 'energia electrica'],
  agua: ['agua', 'aysa', 'hidric', 'saneamiento', 'cloaca'],
  deporte: ['deport'], futbol: ['futbol', 'deport'], cultura: ['cultura', 'cultural', 'teatro', 'museo', 'biblioteca', 'inamu', 'incaa'],
  musica: ['music', 'inamu'], teatro: ['teatro'], museo: ['museo'],
  deuda: ['deuda', 'intereses', 'servicio de la deuda'], escuela: ['escuela', 'escolar', 'educacion', 'educativ'], educacion: ['educacion', 'educativ', 'escuela'],
  vivienda: ['vivienda', 'habitat', 'barrios populares'], obras: ['obra', 'construccion', 'infraestructura'],
  defensa: ['defensa', 'armada', 'ejercito', 'fuerza aerea', 'militar'], ejercito: ['ejercito'],
  avion: ['aerolineas', 'aeronavegacion', 'aviacion', 'aerea', 'fadea', 'eana'], aerolineas: ['aerolineas'],
  correo: ['correo'], comedores: ['comedor', 'alimentari'], alimentos: ['alimentari', 'comedor', 'alimento'],
  carceles: ['penitenciari', 'carcel'], justicia: ['justicia', 'judicial'], congreso: ['legislativ', 'diputados', 'senado'],
  medicamentos: ['medicamento', 'remedio', 'farmac'], vacunas: ['vacuna', 'inmunizacion'],
};

let D = null, items = [], mostrados = 30, ultimo = [];

function raiz(w) { return w.length >= 5 ? w.replace(/(es|s)$/, '') : w; }
function variantes(q) {
  const n = norm(q).trim();
  if (!n) return [];
  const palabras = n.split(' ');
  if (palabras.length === 1) { const r = raiz(n); return (SINONIMOS[n] || SINONIMOS[r] || [r]).map((v) => v.trim().split(' ')); }
  // varias palabras: frase completa (sin palabras vacías), cada palabra con su raíz
  const VACIAS = new Set(['de', 'del', 'la', 'las', 'los', 'el', 'y', 'en', 'para', 'por', 'con', 'que', 'a', 'al', 'n', 'nro', 'no', 'nacional']);
  const ps = palabras.filter((w) => !VACIAS.has(w) && (w.length >= 2 || /\d/.test(w))).map(raiz);
  if (!ps.length) return [];
  // "ruta 40" también figura como "RN 40" o "RN N° 40"
  const k = ps.indexOf('ruta');
  if (k >= 0 && /^\d+$/.test(ps[k + 1] || '')) return [ps, ps.map((w, i) => (i === k ? 'rn' : w))];
  return [ps];
}
// una "variante" es una lista de palabras: todas tienen que aparecer (al inicio de palabra)
// los números tienen que coincidir enteros ("3" no encuentra "34"); las palabras, desde el inicio
const esta = (texto, w) => texto.includes(' ' + w + (/^\d+$/.test(w) ? ' ' : ''));
const tiene = (texto, ps) => ps.every((p) => esta(texto, p));
const algunaEn = (texto, vs) => vs.some((ps) => tiene(texto, ps));

function preparar() {
  for (const p of D.programas) {
    p.ctx = norm([p.j, p.e, p.n].join(' '));
    p.h27 = (p.act27 || []).map((a) => norm(a[0]));
    p.h26 = (p.act26 || []).map((a) => norm(a[0]));
    p.hm = (p.metas || []).map((m) => norm(m[0]));
    p.tipo = 'p';
    items.push(p);
  }
  for (const e of D.entes) { e.ctx = norm(e.n + ' ' + e.tipo); e.tipo2 = e.tipo; e.tipo = 'e'; items.push(e); }
  const provs = new Set();
  D.programas.forEach((p) => (p.prov26 || []).forEach((r) => provs.add(r[0])));
  const orden = [...provs].sort((a, b) => {
    const esp = (x) => /^(Nacional|Interprovincial|No Clasificado|Binacional|Exterior)$/.test(x);
    return esp(a) - esp(b) || a.localeCompare(b, 'es');
  });
  $('#prov').append(...orden.map((p) => el('option', {value: p, text: p})));
  $('#corte').textContent = new Date(D.corte26 + 'T12:00:00').toLocaleDateString('es-AR', {day: 'numeric', month: 'long', year: 'numeric'});
}

// Páginas del sitio que coinciden con la búsqueda (secciones, perfiles, provincias, glosario)
const PAGINAS = (window.PAGINAS || []).map((p) => ({...p, tt: ' ' + norm(p.t) + ' ', kk: ' ' + norm(p.t + ' ' + p.k) + ' '}));
function enSitio(q) {
  const caja = $('#en-sitio');
  if (!caja) return;
  const ps = norm(q).trim().split(' ').filter((w) => w.length >= 3).map(raiz);
  const hits = ps.length ? PAGINAS.filter((p) => tiene(p.kk, ps)).sort((a, b) => tiene(b.tt, ps) - tiene(a.tt, ps)).slice(0, 6) : [];
  caja.hidden = !hits.length;
  caja.replaceChildren(...(hits.length ? [el('span', {class: 'note', text: 'En el sitio:'}), ...hits.map((p) => el('a', {href: p.u, text: p.t}))] : []));
}

function buscar() {
  const q = $('#q').value, prov = $('#prov').value;
  enSitio(q);
  const vs = variantes(q);
  const res = [];
  if (!vs.length) {
    // sin búsqueda: los programas más grandes (o los de la provincia)
    for (const p of D.programas) res.push({x: p, nivel: 'todo'});
  } else {
    for (const x of items) {
      if (x.tipo === 'e') { if (algunaEn(x.ctx, vs)) res.push({x, nivel: 'todo'}); continue; }
      if (algunaEn(x.ctx, vs)) { res.push({x, nivel: 'todo'}); continue; }
      // coincidencia en obras/actividades: la palabra tiene que estar en la actividad (el contexto completa)
      const enHoja = (h) => vs.some((ps) => ps.some((w) => esta(h, w)) && tiene(h + x.ctx, ps));
      const i27 = x.h27.map((h, i) => (enHoja(h) ? i : -1)).filter((i) => i >= 0);
      const i26 = x.h26.map((h, i) => (enHoja(h) ? i : -1)).filter((i) => i >= 0);
      const im = x.hm.map((h, i) => (enHoja(h) ? i : -1)).filter((i) => i >= 0);
      if (i27.length || i26.length) res.push({x, nivel: 'hojas', i27, i26});
      else if (im.length) res.push({x, nivel: 'metas', im});
    }
  }
  const montoProv = (p) => { const r = (p.prov26 || []).find((z) => z[0] === prov); return r ? r : null; };
  let lista = res;
  if (prov) lista = res.filter((r) => r.x.tipo === 'p' && montoProv(r.x));
  const peso = (r) => {
    if (prov) return montoProv(r.x)[1];
    if (r.x.tipo === 'e') return r.x.g27 * 0.999;
    if (r.nivel === 'hojas') return Math.max(sumaHojas(r, 27), sumaHojas(r, 26, 2));
    return Math.max(r.x.a27 || 0, r.x.v26 || 0);
  };
  lista.sort((a, b) => (b.nivel === 'todo') - (a.nivel === 'todo') || peso(b) - peso(a));
  if (!vs.length && !prov) lista = lista.slice(0, 60);
  ultimo = lista; mostrados = 30;
  resumen(lista, vs, q, prov, montoProv);
  pintar();
  try { const u = new URL(location.href); if (q) u.searchParams.set('q', q); else u.searchParams.delete('q'); if (prov) u.searchParams.set('provincia', prov); else u.searchParams.delete('provincia'); history.replaceState(null, '', u); } catch (e) {}
}
function sumaHojas(r, anio, col) {
  const p = r.x;
  if (anio === 27) return (r.i27 || []).reduce((s, i) => s + p.act27[i][1], 0);
  return (r.i26 || []).reduce((s, i) => s + p.act26[i][col || 1], 0);
}

function resumen(lista, vs, q, prov, montoProv) {
  const box = $('#resumen'), est = $('#estado');
  const progs = lista.filter((r) => r.x.tipo === 'p'), entes = lista.filter((r) => r.x.tipo === 'e');
  if (!vs.length && !prov) {
    est.textContent = 'Escribí lo que te interese o tocá un atajo. Abajo, los programas más grandes del presupuesto.';
    box.hidden = true; return;
  }
  if (!lista.length) {
    est.replaceChildren('No encontré «' + q + '» en los programas. Probá con otra palabra o con el nombre del organismo, o ', el('a', {href: '/cuadros?q=' + encodeURIComponent(q), text: 'buscalo en los cuadros del PDF'}), '.');
    box.hidden = true; return;
  }
  const s = {a27: 0, v26: 0, d26: 0};
  for (const r of progs) {
    if (prov) { const m = montoProv(r.x); s.v26 += m[1]; s.d26 += m[2]; continue; }
    if (r.nivel === 'todo') { s.a27 += r.x.a27 || 0; s.v26 += r.x.v26 || 0; s.d26 += r.x.d26 || 0; }
    else if (r.nivel === 'hojas') { s.a27 += sumaHojas(r, 27); s.v26 += sumaHojas(r, 26, 2); s.d26 += sumaHojas(r, 26, 3); }
  }
  const tot = progs.length, partes = [];
  if (tot) partes.push(tot + (tot === 1 ? ' programa' : ' programas'));
  if (entes.length) partes.push(entes.length + (entes.length === 1 ? ' organismo con presupuesto propio' : ' organismos con presupuesto propio'));
  est.replaceChildren((q ? 'Para «' + q + '»' : 'Todo') + (prov ? ' en ' + prov : '') + ': ' + partes.join(' y ') + '. ', el('a', {href: '/cuadros?q=' + encodeURIComponent(q || prov), text: 'Ver también en los cuadros del PDF'}), '.');
  const cif = [];
  if (progs.length) {
    if (!prov) cif.push(cifra('Pedido para 2027', plata(s.a27), null, usd(s.a27, 2027)));
    cif.push(cifra('2026: autorizado hoy' + (prov ? ' en ' + prov : ''), plata(s.v26), null, usd(s.v26, 2026)), cifra('2026: gastado hasta ahora', plata(s.d26) + ' (' + pct(s.d26, s.v26) + ')', null, usd(s.d26, 2026)));
  }
  if (entes.length) { const g = entes.reduce((a, r) => a + r.x.g27, 0); cif.push(cifra('Organismos con presupuesto propio, 2027 (no se suman)', plata(g), null, usd(g, 2027))); }
  box.replaceChildren(
    el('div', {style: 'flex:1 1 100%'}, el('strong', {text: 'Suma de los resultados'}), el('p', {class: 'note', text: prov
      ? 'Lo que el Estado nacional asignó a ' + prov + ' en 2026 en los programas encontrados. No incluye el gasto clasificado como nacional o interprovincial.'
      : 'Suma de los programas y de las obras o actividades que coinciden con la búsqueda. El presupuesto propio de universidades, entes y empresas va aparte porque en parte se financia con esos mismos programas.'})),
    el('div', {class: 'cifras', style: 'flex:1 1 100%'}, ...cif));
  box.hidden = false;
}
function cifra(k, v, barra, u) { return el('div', {class: 'cifra'}, el('div', {class: 'ck', text: k}), el('div', {class: 'cv', text: v}), u ? el('div', {class: 'cu usd', text: '≈ ' + u}) : null, barra || null); }

function marcar(texto, vs) {
  // resalta las palabras buscadas sin tocar el texto original
  const n = texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const rangos = [];
  for (const ps of vs) for (const w of ps) { const re = new RegExp('(^|[^a-z0-9])(' + w.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')' + (/^\d+$/.test(w) ? '(?![0-9])' : ''), 'g'); let m; while ((m = re.exec(n))) rangos.push([m.index + m[1].length, m.index + m[1].length + m[2].length]); }
  if (!rangos.length) return [texto];
  rangos.sort((a, b) => a[0] - b[0]);
  const out = []; let i = 0;
  for (const [a, b] of rangos) { if (a < i) continue; out.push(texto.slice(i, a), el('mark', {text: texto.slice(a, b)})); i = b; }
  out.push(texto.slice(i));
  return out;
}

function pintar() {
  const vs = variantes($('#q').value), prov = $('#prov').value;
  $('#res').replaceChildren(...ultimo.slice(0, mostrados).map((r) => el('li', {}, r.x.tipo === 'e' ? tarjetaEnte(r.x, vs) : tarjeta(r, vs, prov))));
  $('#mas').hidden = ultimo.length <= mostrados;
  $('#mas').textContent = 'Ver más resultados (' + (ultimo.length - mostrados) + ' más)';
}

function tarjeta(r, vs, prov) {
  const p = r.x;
  const org = [p.j, p.e].filter(Boolean).join(' › ');
  const cif = [];
  const var27 = p.a27 != null && p.v26 > 0 ? (p.a27 / p.v26 / (1 + window.CFG.INFLP_JS / 100) - 1) * 100 : null;
  cif.push(cifra('Pedido para 2027', p.a27 == null ? 'No sigue en 2027' : plata(p.a27), null, usd(p.a27, 2027)));
  if (p.v26 != null) {
    cif.push(cifra('2026: aprobado por ley', plata(p.l26), null, usd(p.l26, 2026)), cifra('2026: autorizado hoy', plata(p.v26), null, usd(p.v26, 2026)));
    const ej = p.v26 ? Math.min(100, Math.max(0, p.d26 / p.v26 * 100)) : 0;
    cif.push(cifra('2026: gastado', plata(p.d26) + ' (' + pct(p.d26, p.v26) + ')', el('div', {class: 'barra-ej'}, el('span', {style: 'width:' + ej.toFixed(1) + '%'})), usd(p.d26, 2026)));
  } else cif.push(cifra('2026', 'Programa nuevo o reorganizado'));
  if (prov) { const m = p.prov26.find((z) => z[0] === prov); cif.push(cifra('2026 en ' + prov, plata(m[1]) + ' · gastado ' + plata(m[2]))); }
  const etq = [];
  if (var27 != null && p.a27 != null) etq.push(el('span', {class: 'etq' + (var27 < 0 ? ' warn' : ''), text: 'Variación real 2027 contra lo autorizado en 2026: ' + (Math.round(var27) > 0 ? '+' : Math.round(var27) < 0 ? '−' : '') + nf(0).format(Math.abs(Math.round(var27))) + '%', title: 'Descontando la inflación promedio de ' + window.CFG.INFLP + '% que supone el proyecto.'}));
  const cuerpo = [el('div', {class: 'org', text: org}), el('h3', {}, el('a', {href: '/gasto/' + p.s}, ...marcar(p.n, vs))), p.b ? el('p', {class: 'note', text: p.b}) : null, etq.length ? el('div', {}, ...etq) : null, el('div', {class: 'cifras'}, ...cif)];
  if (r.nivel === 'hojas') {
    const filas = [];
    for (const i of r.i27) filas.push(el('li', {}, el('span', {}, ...marcar(p.act27[i][0], vs)), el('span', {text: '2027: ' + plata(p.act27[i][1])})));
    for (const i of r.i26) { const a = p.act26[i]; filas.push(el('li', {}, el('span', {}, ...marcar(a[0], vs)), el('span', {text: '2026: vigente ' + plata(a[2]) + ' · gastado ' + plata(a[3])}))); }
    const n = filas.length;
    cuerpo.push(el('div', {}, el('strong', {style: 'font-size:var(--fs-cap)', text: n + (n === 1 ? ' obra o actividad coincide' : ' obras o actividades coinciden') + ' (suma 2027: ' + plata(sumaHojas(r, 27)) + ')'}), el('ul', {class: 'hojas'}, ...filas.slice(0, 12))));
    if (n > 12) cuerpo.push(el('p', {class: 'note', text: 'Y ' + (n - 12) + ' más: abrí el detalle para verlas todas.'}));
  }
  if (r.nivel === 'metas') cuerpo.push(el('p', {class: 'note'}, 'Coincide en una meta física: ', ...marcar(p.metas[r.im[0]][0], vs)));
  cuerpo.push(detalle(p, vs));
  return el('article', {class: 'item'}, ...cuerpo);
}

function tabla(cab, filas) {
  return el('div', {class: 'tabla-scroll'}, el('table', {class: 'tabla'}, el('thead', {}, el('tr', {}, ...cab.map((c) => el('th', {text: c})))), el('tbody', {}, ...filas.map((f) => el('tr', {}, ...f.map((c) => (c instanceof Node || Array.isArray(c) ? el('td', {}, ...[].concat(c)) : el('td', {text: c}))))))));
}
function detalle(p, vs) {
  const d = el('details', {class: 'det'}, el('summary', {text: 'Ver el detalle completo'}));
  d.addEventListener('toggle', () => {
    if (!d.open || d.dataset.ok) return; d.dataset.ok = 1;
    const partes = [];
    if (p.act27 && p.act27.length) partes.push(el('h4', {text: '2027: en qué se gasta (' + p.act27.length + ' actividades y obras)'}), tabla(['Actividad u obra', 'Pedido 2027'], p.act27.map((a) => [marcar(a[0], vs), plata(a[1])])));
    if (p.inc27 && p.inc27.length) partes.push(el('h4', {text: '2027: por tipo de gasto'}), tabla(['Tipo de gasto', 'Pedido 2027', '% del programa'], p.inc27.map((a) => [a[0], plata(a[1]), pct(a[1], p.a27)])));
    if (p.metas && p.metas.length) partes.push(el('h4', {text: '2027: metas físicas (qué promete hacer)'}), tabla(['Meta o indicador', 'Unidad', 'Cantidad 2027'], p.metas.map((m) => [marcar(m[0], vs), m[1] || '', nf(Number.isInteger(m[2]) ? 0 : 2).format(m[2])])));
    if (p.act26 && p.act26.length) partes.push(el('h4', {text: '2026: autorizado y gastado por actividad'}), tabla(['Actividad u obra', 'Ley', 'Vigente', 'Gastado', '%'], p.act26.map((a) => [marcar(a[0], vs), plata(a[1]), plata(a[2]), plata(a[3]), pct(a[3], a[2])])));
    if (p.prov26 && p.prov26.length) partes.push(el('h4', {text: '2026: por provincia'}), tabla(['Provincia', 'Vigente', 'Gastado', '%'], p.prov26.map((a) => [a[0], plata(a[1]), plata(a[2]), pct(a[2], a[1])])));
    const link = el('button', {class: 'btn', type: 'button', text: 'Copiar link a este programa'});
    link.addEventListener('click', async () => { const u = SITE + '/programas?q=' + encodeURIComponent(p.n); try { await navigator.clipboard.writeText(u); toast('Link copiado'); } catch (e) { prompt('Copiá el link:', u); } });
    partes.push(el('div', {class: 'acciones'}, el('a', {class: 'btn primary', href: '/gasto/' + p.s, text: 'Ver la página completa'}), link, el('a', {class: 'btn', href: '/cuadros?q=' + encodeURIComponent(p.e || p.j), text: 'Buscar el organismo en los cuadros'})));
    d.append(...partes);
    if (window.va) window.va('event', {name: 'programa', data: {n: p.n.slice(0, 60)}});
  });
  return d;
}

function tarjetaEnte(e, vs) {
  const cif = [cifra('Gasto total 2027 (proyecto)', plata(e.g27), null, usd(e.g27, 2027))];
  if (e.g26 != null) cif.push(cifra('Gasto total 2026 (ley)', plata(e.g26) + (e.g26 > 0 ? ' · ' + (e.g27 >= e.g26 ? '+' : '') + nf(0).format((e.g27 / e.g26 - 1) * 100) + '% nominal' : ''), null, usd(e.g26, 2026)));
  cif.push(...(e.det || []).map((d) => cifra(d[0] + ' 2027', plata(d[1]))));
  return el('article', {class: 'item'},
    el('div', {class: 'org', text: e.tipo2 + ' · tiene presupuesto propio'}),
    el('h3', {}, el('a', {href: '/gasto/' + e.s}, ...marcar(e.n, vs))),
    el('div', {class: 'cifras'}, ...cif),
    e.nota ? el('p', {class: 'note', text: e.nota}) : null,
    e.g26 != null ? el('p', {class: 'note', text: 'La ley 2026 se armó suponiendo 10,1% de inflación y el año cerraría cerca de ' + window.CFG.INFL26 + '%: por eso la suba nominal contra la ley no dice si hay más o menos recursos reales.'}) : null,
    el('div', {class: 'acciones'}, el('a', {class: 'btn primary', href: '/gasto/' + e.s, text: 'Ver la página completa'}), el('a', {class: 'btn', href: '/cuadros#p' + e.pag, text: 'Cuadro 2027 (pág. ' + e.pag + ')'}), e.pag26 ? el('a', {class: 'btn', href: '/cuadros#ley2026-p' + e.pag26, text: 'Cuadro de la ley 2026 (pág. ' + e.pag26 + ')'}) : null));
}

let espera;
$('#q').addEventListener('input', () => { clearTimeout(espera); espera = setTimeout(buscar, 200); });
$('#prov').addEventListener('change', buscar);
$('#mas').addEventListener('click', () => { mostrados += 30; pintar(); });
$('#atajos').addEventListener('click', (e) => { const b = e.target.closest('button[data-q]'); if (!b) return; $('#q').value = b.dataset.q; buscar(); if (window.va) window.va('event', {name: 'atajo_programas', data: {q: b.dataset.q}}); });

fetch('/datos/programas.json').then((r) => r.json()).then((d) => {
  D = d; preparar();
  const u = new URL(location.href);
  if (u.searchParams.get('q')) $('#q').value = u.searchParams.get('q');
  if (u.searchParams.get('provincia')) $('#prov').value = u.searchParams.get('provincia');
  buscar();
}).catch(() => { $('#estado').textContent = 'No se pudieron cargar los datos. Recargá la página.'; });
