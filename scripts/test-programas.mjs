// Prueba del buscador por programa. Uso: CHROME_PATH=... node scripts/test-programas.mjs <carpeta-capturas>
import http from 'node:http'; import { readFile } from 'node:fs/promises'; import path from 'node:path'; import { chromium } from 'playwright';
const raiz = process.cwd(), out = process.argv[2] || '.';
const tipos = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.webp': 'image/webp', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.webp': 'image/webp' };
const server = http.createServer(async (req, res) => { let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html'; if (!path.extname(p)) p += '.html';
  try { const b = await readFile(path.join(raiz, p)); res.writeHead(200, { 'content-type': tipos[path.extname(p)] || 'application/octet-stream' }); res.end(b); } catch { res.writeHead(404); res.end(); } });
await new Promise((r) => server.listen(0, r)); const base = `http://127.0.0.1:${server.address().port}`;
const b = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
const p = await (await b.newContext({ viewport: { width: 1200, height: 900 } })).newPage(); const errs = [];
p.on('pageerror', (e) => errs.push(e.message)); p.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
const ver = async (q, prov) => {
  await p.goto(base + '/programas?q=' + encodeURIComponent(q) + (prov ? '&provincia=' + encodeURIComponent(prov) : ''));
  await p.waitForFunction(() => !document.querySelector('#estado').textContent.startsWith('Cargando'));
  return p.evaluate(() => ({ estado: document.querySelector('#estado').innerText, suma: document.querySelector('#resumen').hidden ? '' : document.querySelector('#resumen .cifras').innerText.replace(/\n/g, ' '),
    top: [...document.querySelectorAll('#res > li')].slice(0, 4).map((li) => li.querySelector('h3').innerText + ' | ' + li.querySelector('.cifras').innerText.replace(/\n/g, ' ').slice(0, 160)) }));
};
for (const [q, prov] of (process.env.QS ? JSON.parse(process.env.QS) : [['cine'], ['rutas'], ['Ruta 40'], ['universidad de la matanza'], ['pami'], ['trenes'], ['rutas', 'Córdoba'], ['', 'Salta'], ['zzzxx']])) console.log(JSON.stringify([q, prov, await ver(q, prov)], null, 1));
await ver('rutas'); await p.click('#res details summary'); await p.screenshot({ path: out + '/prog-rutas.png', fullPage: false });
await p.evaluate(() => document.querySelector('#res details').scrollIntoView()); await p.screenshot({ path: out + '/prog-rutas-det.png' });
await p.setViewportSize({ width: 390, height: 800 }); await ver('cine');
console.log('ancho movil:', await p.evaluate(() => document.documentElement.scrollWidth)); await p.screenshot({ path: out + '/prog-cine-movil.png', fullPage: true });
await p.setViewportSize({ width: 1200, height: 900 });
await p.goto(base + '/cuadros?q=incaa'); await p.waitForTimeout(1200); console.log('cuadros q:', await p.evaluate(() => document.querySelector('#estado').innerText));
await p.goto(base + '/cuadros#ley2026-p82'); await p.waitForTimeout(1200);
console.log('ley 2026:', await p.evaluate(() => [document.querySelector('#vmeta').innerText, document.querySelector('#vtitulo').innerText, document.querySelector('#vimg').naturalWidth, location.hash]));
await p.screenshot({ path: out + '/cuadros-2026.png' });
await p.click('#sig'); await p.waitForTimeout(500); console.log('siguiente:', await p.evaluate(() => [document.querySelector('#vtitulo').innerText, location.hash]));
await p.click('.docs button[data-doc="2027"]'); await p.waitForTimeout(500); console.log('volver 2027:', await p.evaluate(() => [document.querySelector('#vmeta').innerText, location.hash]));
const reales = errs.filter((e) => !e.includes('404')); console.log('ERRORES', JSON.stringify(reales)); await b.close(); server.close(); if (reales.length) process.exit(1);
