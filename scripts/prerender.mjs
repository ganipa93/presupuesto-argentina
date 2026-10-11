// Deja el contenido escrito en index.html (para buscadores y vistas previas) y genera og.png.
// Uso: node scripts/prerender.mjs   (después de python3 scripts/build.py)
import http from 'node:http';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tipos = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png' };
const server = http.createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p.endsWith('/')) p += 'index.html';
  try { const body = await readFile(path.join(raiz, p)); res.writeHead(200, { 'content-type': tipos[path.extname(p)] || 'application/octet-stream' }); res.end(body); }
  catch { res.writeHead(404); res.end(); }
});
await new Promise((r) => server.listen(0, r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
const errores = [];
page.on('pageerror', (e) => errores.push(e.message));
await page.goto(base + '/', { waitUntil: 'load' });
await page.waitForSelector('#claves .clave');
let htmlRender = await page.content();
if (!htmlRender.toLowerCase().startsWith('<!doctype')) htmlRender = '<!doctype html>\n' + htmlRender;
await writeFile(path.join(raiz, 'index.html'), htmlRender);
const og = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await og.goto(base + '/scripts/.og-render.html', { waitUntil: 'load' });
await og.evaluate(() => document.fonts.ready);
await og.screenshot({ path: path.join(raiz, 'og.png') });
await browser.close();
server.close();
if (errores.length) { console.error('Errores en la página:', errores); process.exit(1); }
console.log('Listo: index.html con contenido escrito y og.png');
