// Renders showreel.html to PNG frames with headless Chromium (Playwright).
//
//   node docs/showreel/src/render.mjs --out /tmp/frames              all 900 frames, 1080p, motion blur
//   node docs/showreel/src/render.mjs --out /tmp/stills --times 1.2,4.3 --scale 0.5   quick stills
//
// Frames go to --out (default: a folder in the system temp dir; ~2 GB, keep them out of the repo).
//
// Options: --scale (1 = 1920x1080), --sub (motion-blur samples per frame; default: 8, more in fast moves),
// --from/--to (frame range), --workers (parallel pages, default 4).
// Needs Node 18+ and Playwright's Chromium: `npm i -g playwright && npx playwright install chromium`.
// encode.sh then turns the frames into the MP4 and the WebP.
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  try { return require('playwright'); } catch {}
  const globalRoot = execSync('npm root -g').toString().trim();
  return require(path.join(globalRoot, 'playwright'));
}

const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]);
  return acc;
}, []));
const scale = +(args.scale || 1);
const sub = args.sub ? +args.sub : 0;          // 0 = let the page choose per frame
const workers = +(args.workers || 4);
const out = path.resolve(args.out || path.join(os.tmpdir(), 'gym-tracker-showreel-frames'));
fs.mkdirSync(out, { recursive: true });

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.json': 'application/json', '.mp3': 'audio/mpeg' };
const server = http.createServer((req, res) => {
  const p = path.join(REPO, decodeURIComponent(new URL(req.url, 'http://x').pathname));
  if (!p.startsWith(REPO) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});
await new Promise(ok => server.listen(0, '127.0.0.1', ok));
const url = `http://127.0.0.1:${server.address().port}/docs/showreel/src/showreel.html?render&scale=${scale}`;

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ args: ['--disable-gpu', '--force-color-profile=srgb'] });

async function openPage() {
  const page = await browser.newPage({ viewport: { width: 400, height: 300 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(url);
  await page.waitForFunction(() => window.READY || window.LOAD_ERROR, null, { timeout: 60000 });
  const err = await page.evaluate(() => window.LOAD_ERROR);
  if (err) throw new Error(err);
  return page;
}
async function grab(page, fn, arg, file) {
  const data = await page.evaluate(([f, a]) => { window[f](...a); return document.getElementById('c').toDataURL('image/png'); }, [fn, arg]);
  fs.writeFileSync(file, Buffer.from(data.split(',')[1], 'base64'));
}

const started = Date.now();
if (args.times) {
  const page = await openPage();
  for (const t of String(args.times).split(',').map(Number)) {
    await grab(page, 'renderAt', [t], path.join(out, `t_${t.toFixed(3).padStart(6, '0')}.png`));
  }
} else {
  const probe = await openPage();
  const meta = await probe.evaluate(() => window.META);
  await probe.close();
  const total = Math.round(meta.DUR * meta.FPS);
  const from = +(args.from || 0), to = Math.min(total, +(args.to || total));
  const frames = Array.from({ length: to - from }, (_, k) => from + k);
  let done = 0;
  await Promise.all(Array.from({ length: workers }, async (_, w) => {
    const page = await openPage();
    for (let k = w; k < frames.length; k += workers) {
      const i = frames[k];
      const n = sub || await page.evaluate(k => window.subFor(k), i);
      await grab(page, 'renderFrame', [i, n], path.join(out, `f_${String(i).padStart(5, '0')}.png`));
      if (++done % 30 === 0) process.stdout.write(`\r${done}/${frames.length} frames`);
    }
  }));
  fs.writeFileSync(path.join(out, 'meta.json'), JSON.stringify(meta, null, 2));
}
console.log(`\ndone in ${((Date.now() - started) / 1000).toFixed(1)} s -> ${out}`);
await browser.close();
server.close();
