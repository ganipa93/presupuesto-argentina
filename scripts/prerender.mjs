// Deja el contenido escrito en cada sección de la portada (para buscadores y vistas previas)
// y genera las imágenes para redes (og.png y las de cada página de /gasto y /provincias).
// Uso: node scripts/prerender.mjs   (después de python3 scripts/build.py)
import http from 'node:http';
import { readFile, writeFile, mkdir, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { chromium } from 'playwright';

const raiz = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const tipos = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp' };
// index.html recién armado por build.py es la plantilla de todas las secciones
const plantilla = await readFile(path.join(raiz, 'index.html'));
const server = http.createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (p === '/' || !path.extname(p)) { res.writeHead(200, { 'content-type': tipos['.html'] }); res.end(plantilla); return; }
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
await page.waitForSelector('#claves .clave', { state: 'attached' });
const rutas = await page.evaluate(() => [...Object.values(SECCIONES).map((s) => s.ruta), ...DATA.impacto.map((p) => '/que-me-cambia/' + p.id)]);
for (const ruta of rutas) {
  await page.goto(base + ruta, { waitUntil: 'load' });
  await page.waitForSelector('#claves .clave', { state: 'attached' });
  let html = await page.content();
  if (!html.toLowerCase().startsWith('<!doctype')) html = '<!doctype html>\n' + html;
  const archivo = ruta === '/' ? 'index.html' : ruta.slice(1) + '.html';
  await mkdir(path.dirname(path.join(raiz, archivo)), { recursive: true });
  await writeFile(path.join(raiz, archivo), html);
}

// Imagen general para redes
const og = await browser.newPage({ viewport: { width: 1200, height: 630 } });
await og.goto(base + '/scripts/.og-render.html', { waitUntil: 'load' });
await og.evaluate(() => document.fonts.ready);
await og.screenshot({ path: path.join(raiz, 'og.png') });

// Imágenes de cada página de detalle: solo se rehacen las que cambiaron
let hechas = 0;
try {
  const trabajos = JSON.parse(await readFile(path.join(raiz, 'scripts/.og-paginas.json'), 'utf-8'));
  const manifiesto = JSON.parse(await readFile(path.join(raiz, 'og/manifiesto.json'), 'utf-8').catch(() => '{}'));
  // Si cambia el diseño de la imagen, se rehacen todas
  const plantillaOg = createHash('sha1').update(await readFile(path.join(raiz, 'src/og-pagina.html'))).digest('hex').slice(0, 8);
  await og.goto(base + '/src/og-pagina.html', { waitUntil: 'load' });
  await og.evaluate(() => document.fonts.ready);
  for (const t of trabajos) {
    const h = createHash('sha1').update(plantillaOg + JSON.stringify(t)).digest('hex').slice(0, 12);
    const destino = path.join(raiz, 'og', t.archivo);
    const existe = await access(destino).then(() => true, () => false);
    if (manifiesto[t.archivo] === h && existe) continue;
    await og.evaluate((d) => window.pintar(d), t);
    await mkdir(path.dirname(destino), { recursive: true });
    await og.screenshot({ path: destino, type: 'jpeg', quality: 68 });
    manifiesto[t.archivo] = h; hechas++;
  }
  await writeFile(path.join(raiz, 'og/manifiesto.json'), JSON.stringify(manifiesto, null, 0));
} catch (e) { if (e.code !== 'ENOENT') throw e; }

await browser.close();
server.close();
if (errores.length) { console.error('Errores en la página:', errores); process.exit(1); }
console.log(`Listo: ${rutas.length} secciones con contenido escrito, og.png y ${hechas} imágenes de páginas nuevas o cambiadas`);
