// 以 headless Chromium 取得 BePTT (y_studio.ka5983.ptt2) 的下載連結並下載
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT_DIR = '/home/user/29988122/beptt-mod/apk';
const PKG = 'y_studio.ka5983.ptt2';

(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    acceptDownloads: true,
  });
  const page = await ctx.newPage();

  const candidates = new Set();
  page.on('response', (resp) => {
    const u = resp.url();
    if (/\.(apk|xapk|apkm)(\?|$)/i.test(u)) candidates.add(u);
  });

  const url = `https://apkpure.com/beptt/${PKG}/download`;
  console.log('GOTO', url);
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  } catch (e) { console.log('goto err', e.message); }
  await page.waitForTimeout(6000);

  // 蒐集頁面上所有可能的下載連結
  const hrefs = await page.$$eval('a', as => as.map(a => a.href).filter(Boolean));
  const dlLinks = hrefs.filter(h => /\.(apk|xapk|apkm)(\?|$)/i.test(h) || /\/down\//i.test(h) || /d\.apkpure/i.test(h));
  console.log('PAGE_TITLE', await page.title());
  console.log('DL_LINKS', JSON.stringify([...new Set(dlLinks)].slice(0, 20), null, 2));
  console.log('NET_CANDIDATES', JSON.stringify([...candidates].slice(0, 20), null, 2));

  // 嘗試點擊下載按鈕以觸發實際下載
  let saved = null;
  try {
    const dlPromise = page.waitForEvent('download', { timeout: 45000 }).catch(() => null);
    // 常見下載按鈕
    const btn = await page.$('a.download-start-btn, a#download_link, a.da, a[href*="d.apkpure"], a[href*=".apk"], a[href*=".xapk"]');
    if (btn) { console.log('clicking button'); await btn.click({ timeout: 10000 }).catch(e => console.log('click err', e.message)); }
    const dl = await dlPromise;
    if (dl) {
      const fn = dl.suggestedFilename() || `${PKG}.apk`;
      const dest = path.join(OUT_DIR, fn);
      await dl.saveAs(dest);
      saved = dest;
      console.log('SAVED_VIA_DOWNLOAD', dest, fs.statSync(dest).size);
    }
  } catch (e) { console.log('download flow err', e.message); }

  console.log('RESULT_SAVED', saved);
  await browser.close();
})();
