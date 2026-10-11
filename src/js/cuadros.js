// cuadros.js — se publica en /js/cuadros.js (lo copia scripts/build.py). Los datos llegan en window.CFG.
const DOCS = {
  '2027': {idx: window.CFG.INDICE, base: '/cuadros', pdf: '/fuentes/proyecto-presupuesto-2027.pdf', nombre: 'Proyecto 2027', hash: 'p',
    nota: 'La imagen es la página original del proyecto. El texto y la tabla en CSV se extraen automáticamente: ante cualquier diferencia, vale la imagen.'},
  '2026': {idx: window.CFG.INDICE26, base: '/cuadros/2026', pdf: '/fuentes/ley-27798-presupuesto-2026.pdf', nombre: 'Ley 2026', hash: 'ley2026-p',
    nota: 'La imagen es la página de la ley sancionada (escaneo firmado). El texto se obtuvo por reconocimiento óptico (OCR) y solo sirve para buscar: los números valen en la imagen.'},
};
const SITE = window.CFG.SITE;
const $ = (s) => document.querySelector(s);
const pad = (n) => String(n).padStart(3, '0');
const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const SINONIMOS = {cine: ['cine', 'cinemato', 'incaa', 'audiovisual'], rutas: ['ruta', 'vialidad', 'vial', 'corredores viales'], universidad: ['universidad'],
  pami: ['inssjp', 'pami', 'jubilados y pensionados'], empresas: ['empresas del estado', 'empresas y sociedades'], cargos: ['recursos humanos'],
  subsidios: ['subsidio'], trenes: ['ferrocarril', 'ferroviari', 'trenes'], musica: ['musica', 'inamu'], teatro: ['teatro'], futbol: ['futbol', 'deporte']};
let doc = '2027', actual = null, datos = null, textos = null;
function toast(m) { const t = $('#toast'); t.textContent = m; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, 2000); }

function elegirDoc(d) {
  doc = d;
  document.querySelectorAll('.docs button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.doc === d)));
  document.querySelectorAll('.indice .lista').forEach((l) => { l.hidden = l.dataset.doc !== d; });
  $('#vnota').textContent = DOCS[d].nota;
}
async function mostrar(d, p, desplazar) {
  const D = DOCS[d], x = D.idx.find((i) => i.p === p); if (!x) return;
  if (d !== doc) elegirDoc(d);
  actual = {d, ...x};
  $('#vtitulo').textContent = x.t;
  $('#vmeta').textContent = D.nombre + ' · ' + x.s + ' · Página ' + x.p + ' del PDF';
  const img = $('#vimg');
  img.width = x.w; img.height = x.h; img.alt = D.nombre + ', página ' + x.p + ': ' + x.t;
  img.src = D.base + '/img/p' + pad(x.p) + '.webp';
  $('#pdf').href = D.pdf + '#page=' + x.p;
  document.querySelectorAll('.indice a').forEach((a) => a.setAttribute('aria-current', String(a.dataset.doc === d && a.dataset.p == x.p)));
  const enlace = document.querySelector('.indice a[data-doc="' + d + '"][data-p="' + x.p + '"]');
  if (enlace) { enlace.closest('details').open = true; }
  try { history.replaceState(null, '', location.pathname + location.search + '#' + D.hash + x.p); } catch (e) {}
  $('#vtexto').hidden = true; $('#vertexto').textContent = 'Ver texto';
  datos = null; $('#csv').hidden = true;
  try { datos = await (await fetch(D.base + '/paginas/p' + pad(x.p) + '.json')).json(); } catch (e) {}
  if (datos && actual.p === x.p && actual.d === d) { $('#vtexto').textContent = datos.texto; $('#csv').hidden = !datos.tabla; }
  if (desplazar) $('#visor').scrollIntoView({behavior: 'smooth', block: 'start'});
  if (window.va) window.va('event', {name: 'cuadro', data: {doc: d, pagina: x.p}});
}
function mover(dl) {
  if (!actual) return;
  const lista = DOCS[actual.d].idx.filter((i) => !$('#solo').checked || i.c);
  const k = lista.findIndex((i) => i.p === actual.p);
  const n = lista[Math.min(lista.length - 1, Math.max(0, (k < 0 ? 0 : k) + dl))];
  if (n) mostrar(actual.d, n.p, false);
}
$('#ant').addEventListener('click', () => mover(-1));
$('#sig').addEventListener('click', () => mover(1));
$('#zoom').addEventListener('click', () => { const v = $('#visor').classList.toggle('zoom'); $('#zoom').textContent = v ? 'Ajustar al ancho' : 'Ampliar'; });
$('#vertexto').addEventListener('click', () => { const t = $('#vtexto'); t.hidden = !t.hidden; $('#vertexto').textContent = t.hidden ? 'Ver texto' : 'Ocultar texto'; });
$('#link').addEventListener('click', async () => { const u = SITE + '/cuadros#' + (actual ? DOCS[actual.d].hash + actual.p : ''); try { await navigator.clipboard.writeText(u); toast('Link copiado'); } catch (e) { prompt('Copiá el link:', u); } });
$('#csv').addEventListener('click', () => {
  if (!datos || !datos.tabla) return;
  const csv = datos.tabla.map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""') + '"').join(';')).join('\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + csv], {type: 'text/csv;charset=utf-8'}));
  a.download = 'presupuesto-2027-pagina-' + datos.pagina + '.csv'; document.body.append(a); a.click(); a.remove();
});
document.querySelector('.indice').addEventListener('click', (e) => {
  const b = e.target.closest('.docs button'); if (b) { elegirDoc(b.dataset.doc); const pri = DOCS[b.dataset.doc].idx.find((i) => i.c) || DOCS[b.dataset.doc].idx[0]; mostrar(b.dataset.doc, pri.p, false); return; }
  const a = e.target.closest('a[data-p]'); if (!a) return; e.preventDefault(); mostrar(a.dataset.doc, Number(a.dataset.p), window.innerWidth < 860);
});
$('#solo').addEventListener('change', () => document.body.classList.toggle('solo-cuadros', $('#solo').checked));
document.body.classList.add('solo-cuadros');

async function buscar(q) {
  const res = $('#resultados'), est = $('#estado');
  q = q.trim();
  if (norm(q).length < 3) { res.replaceChildren(); est.textContent = 'Escribí al menos 3 letras. Busca en el texto de todas las páginas de los dos documentos, sin importar tildes ni mayúsculas.'; return; }
  if (!textos) {
    est.textContent = 'Cargando el texto de las páginas…';
    try {
      const [t27, t26] = await Promise.all(['/cuadros/texto.json', '/cuadros/2026/texto.json'].map((u) => fetch(u).then((r) => r.json())));
      textos = [...Object.entries(t27).map(([p, s]) => ['2027', Number(p), s, norm(s)]), ...Object.entries(t26).map(([p, s]) => ['2026', Number(p), s, norm(s)])];
    } catch (e) { est.textContent = 'No se pudo cargar el buscador. Probá de nuevo.'; return; }
  }
  const nq = norm(q);
  let variantes = SINONIMOS[nq] || [nq];
  const contar = (vs, todas) => {
    const out = [];
    for (const [d, p, s, n] of textos) {
      let cuenta = 0, pos = -1, presentes = 0;
      for (const v of vs) { let i = n.indexOf(v); if (i >= 0) { presentes++; if (pos < 0 || i < pos) pos = i; } while (i >= 0) { cuenta++; i = n.indexOf(v, i + v.length); } }
      if (cuenta && (!todas || presentes === vs.length)) out.push({d, p, s, pos, cuenta});
    }
    return out;
  };
  let hallados = contar(variantes, false);
  if (!hallados.length && nq.includes(' ')) {
    // si la frase exacta no aparece, se buscan todas las palabras en la misma página
    const VACIAS = new Set(['de', 'del', 'la', 'las', 'los', 'el', 'y', 'en', 'para', 'por', 'con', 'que', 'a', 'al']);
    variantes = nq.split(/\s+/).filter((w) => w.length >= 3 && !VACIAS.has(w));
    if (variantes.length) hallados = contar(variantes, true);
  }
  hallados.sort((a, b) => b.cuenta - a.cuenta || b.d.localeCompare(a.d) || a.p - b.p);
  const n27 = hallados.filter((h) => h.d === '2027').length, n26 = hallados.length - n27;
  est.textContent = hallados.length ? 'Aparece en ' + n27 + ' página' + (n27 === 1 ? '' : 's') + ' del proyecto 2027 y ' + n26 + ' de la ley 2026' + (variantes.length > 1 ? ' (también busqué: ' + variantes.join(', ') + ')' : '') + '. Tocá una para verla.' : 'No aparece en ninguno de los dos documentos. Probá con otra palabra o con el nombre del organismo.';
  res.replaceChildren(...hallados.slice(0, 50).map((h) => {
    const x = DOCS[h.d].idx.find((i) => i.p === h.p) || {t: '', s: ''};
    const a = document.createElement('a'); a.href = '#' + DOCS[h.d].hash + h.p;
    const tt = document.createElement('strong'); const etq = document.createElement('span'); etq.className = 'doc'; etq.textContent = DOCS[h.d].nombre; tt.append(etq, x.t);
    const meta = document.createElement('div'); meta.className = 'meta'; meta.textContent = 'Página ' + h.p + ' · ' + x.s + ' · ' + h.cuenta + (h.cuenta > 1 ? ' coincidencias' : ' coincidencia');
    const sn = document.createElement('div'); sn.className = 'meta';
    const ini = Math.max(0, h.pos - 70), fin = Math.min(h.s.length, h.pos + 110);
    const largo = variantes.find((v) => norm(h.s).indexOf(v) === h.pos)?.length || nq.length;
    sn.append((ini ? '…' : '') + h.s.slice(ini, h.pos));
    const m = document.createElement('mark'); m.textContent = h.s.slice(h.pos, h.pos + largo); sn.append(m, h.s.slice(h.pos + largo, fin) + (fin < h.s.length ? '…' : ''));
    a.append(tt, meta, sn);
    a.addEventListener('click', (e) => { e.preventDefault(); mostrar(h.d, h.p, true); });
    const li = document.createElement('li'); li.append(a); return li;
  }));
  if (window.va) window.va('event', {name: 'busqueda', data: {q: nq.slice(0, 40)}});
}
let espera;
$('#q').addEventListener('input', (e) => { clearTimeout(espera); espera = setTimeout(() => buscar(e.target.value), 250); });
$('#atajos').addEventListener('click', (e) => { const b = e.target.closest('button[data-q]'); if (!b) return; $('#q').value = b.dataset.q; buscar(b.dataset.q); });
const desdeHash = () => { const h = location.hash.match(/^#(ley2026-)?p(\d+)$/); return h ? [h[1] ? '2026' : '2027', Number(h[2])] : null; };
window.addEventListener('hashchange', () => { const h = desdeHash(); if (h && (!actual || actual.d !== h[0] || actual.p !== h[1])) mostrar(h[0], h[1], false); });
const h0 = desdeHash() || ['2027', 93];
mostrar(h0[0], h0[1], false);
try { const q0 = new URL(location.href).searchParams.get('q'); if (q0) { $('#q').value = q0; buscar(q0); } } catch (e) {}
