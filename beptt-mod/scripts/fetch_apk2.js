const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/home/user/29988122/beptt-mod/apk';
const PKG = 'y_studio.ka5983.ptt2';

const STEALTH = () => {
  Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  Object.defineProperty(navigator, 'languages', { get: () => ['zh-TW', 'zh', 'en-US', 'en'] });
  Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
  window.chrome = { runtime: {} };
  const orig = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function (p) {
    if (p === 37445) return 'Intel Inc.';
    if (p === 37446) return 'Intel Iris OpenGL Engine';
    return orig.call(this, p);
  };
};

async function tryHost(ctx, url) {
  const page = await ctx.newPage();
  const candidates = new Set();
  page.on('response', (r) => { const u = r.url(); if (/\.(apk|xapk|apkm)(\?|$)/i.test(u)) candidates.add(u); });
  console.log('\n==== GOTO', url);
  try { await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }); } catch (e) { console.log('goto err', e.message); }
  // Cloudflare 等待輪詢
  for (let i = 0; i < 15; i++) {
    const t = await page.title().catch(() => '');
    if (!/just a moment|attention required|checking|請稍候/i.test(t)) { console.log('passed CF, title=', t); break; }
    console.log('waiting CF...', i, t);
    await page.waitForTimeout(2500);
  }
  await page.waitForTimeout(3000);
  const title = await page.title().catch(() => '');
  const hrefs = await page.$$eval('a', as => as.map(a => a.href).filter(Boolean)).catch(() => []);
  const dlLinks = [...new Set(hrefs.filter(h => /\.(apk|xapk|apkm)(\?|$)/i.test(h) || /\/down(load)?\//i.test(h) || /d\.apkpure|download\.apk/i.test(h)))];
  console.log('TITLE', title);
  console.log('DL_LINKS', JSON.stringify(dlLinks.slice(0, 25), null, 2));
  console.log('NET', JSON.stringify([...candidates].slice(0, 10)));

  // 嘗試觸發下載
  let saved = null;
  try {
    const dlPromise = page.waitForEvent('download', { timeout: 60000 }).catch(() => null);
    const btn = await page.$('a.download-start-btn, a#download_link, a.da, a[href$=".apk"], a[href$=".xapk"], a[href*="d.apkpure"]');
    if (btn) { await btn.click({ timeout: 10000 }).catch(e => console.log('click err', e.message)); }
    const dl = await dlPromise;
    if (dl) {
      const fn = dl.suggestedFilename() || `${PKG}.apk`;
      const dest = path.join(OUT_DIR, fn);
      await dl.saveAs(dest);
      saved = dest;
      console.log('SAVED', dest, fs.statSync(dest).size);
    }
  } catch (e) { console.log('dl err', e.message); }
  await page.close();
  return saved;
}

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-blink-features=AutomationControlled'] });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'zh-TW', timezoneId: 'Asia/Taipei', viewport: { width: 1366, height: 768 }, acceptDownloads: true,
    extraHTTPHeaders: { 'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8' },
  });
  await ctx.addInitScript(STEALTH);

  const targets = [
    `https://apkpure.com/beptt/${PKG}/download`,
    `https://apkpure.com/beptt/${PKG}`,
    `https://apkfab.com/beptt/${PKG}`,
  ];
  let saved = null;
  for (const t of targets) { saved = await tryHost(ctx, t); if (saved) break; }
  console.log('\nRESULT_SAVED', saved);
  await browser.close();
})();
