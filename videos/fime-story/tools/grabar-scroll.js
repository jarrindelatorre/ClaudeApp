const { chromium } = require('playwright');
// curva de scroll (segundo → px CSS): nunca se detiene; lento en lo visual, rápido en el formulario
const K = [[0,0],[3,380],[6,1450],[9,2350],[12,3250],[15,4250],[18,5150],[21,7650],[24,9250],[26.6,10950],[28.4,120],[30,0]];
function pchip(t) { // Hermite monótono por tramos
  let i = 0; while (i < K.length - 2 && t > K[i + 1][0]) i++;
  const [t0, y0] = K[i], [t1, y1] = K[i + 1], h = t1 - t0, s = (t - t0) / h;
  const sl = (a, b) => (K[b][1] - K[a][1]) / (K[b][0] - K[a][0]);
  const m = (j) => { if (j === 0 || j === K.length - 1) return 0; const a = sl(j - 1, j), b = sl(j, j + 1); return a * b <= 0 ? 0 : (2 * a * b) / (a + b); };
  const m0 = m(i), m1 = m(i + 1), s2 = s * s, s3 = s2 * s;
  return (2*s3-3*s2+1)*y0 + (s3-2*s2+s)*h*m0 + (-2*s3+3*s2)*y1 + (s3-s2)*h*m1;
}
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 430, height: 765 }, deviceScaleFactor: 1080 / 430, isMobile: true, hasTouch: true });
  const p = await ctx.newPage();
  await p.goto('https://festivalesmeraldas.com/', { waitUntil: 'networkidle', timeout: 90000 });
  // precargar lazy-load
  const H = await p.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < H; y += 400) { await p.evaluate(v => window.scrollTo(0, v), y); await p.waitForTimeout(120); }
  await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(1500);
  const cdp = await ctx.newCDPSession(p);
  await cdp.send('Animation.enable'); await cdp.send('Animation.setPlaybackRate', { playbackRate: 0.3 });
  const FPS = 30, N = 30 * FPS;
  for (let f = 0; f < N; f++) {
    const y = Math.max(0, pchip(f / FPS));
    await p.evaluate(v => { window.scrollTo(0, v); return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }, y);
    await p.screenshot({ path: `${process.argv[2]}/f${String(f).padStart(4, '0')}.jpg`, type: 'jpeg', quality: 90 });
  }
  await b.close();
})();
