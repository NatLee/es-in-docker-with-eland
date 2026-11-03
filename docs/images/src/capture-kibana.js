// Takes the Kibana Discover screenshots in the README (light and dark).
//
// Run it after the quick start, the smoke test and the data view request from the README, with a
// Chromium-based browser and puppeteer-core installed somewhere outside this repository:
//   npm install --prefix /tmp/capture puppeteer-core
//   NODE_PATH=/tmp/capture/node_modules BROWSER=/path/to/chrome-or-edge \
//     node docs/images/src/capture-kibana.js .env /tmp/kibana-light.png light
//   ... same with "dark", then: magick kibana-light.png -quality 85 -define webp:method=6 kibana-discover-light.webp
// Set USER_DATA_DIR to reuse a browser profile folder. The script reads ELASTIC_PASSWORD and
// KIBANA_PORT from the env file and never prints them.
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const [envFile = '.env', out = 'kibana.png', theme = 'light'] = process.argv.slice(2);
const env = Object.fromEntries(fs.readFileSync(envFile, 'utf8').split(/\r?\n/)
  .filter((line) => /^[A-Z_]+=/.test(line)).map((line) => [line.slice(0, line.indexOf('=')), line.slice(line.indexOf('=') + 1)]));
const base = `http://localhost:${env.KIBANA_PORT || 5601}`;
// The same link as the README: the tutorial data view, all of 2024, histogram split by index.
const discover = "/app/discover#/?_g=(time:(from:'2024-01-01T00:00:00.000Z',to:'2025-01-01T00:00:00.000Z'))"
  + '&_a=(dataSource:(dataViewId:eland-tutorial,type:dataView),breakdownField:_index)';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.BROWSER,
    headless: true,
    userDataDir: process.env.USER_DATA_DIR || fs.mkdtempSync(path.join(require('os').tmpdir(), 'kibana-capture-')),
    args: ['--hide-scrollbars', '--lang=en-US'],
    defaultViewport: { width: 1440, height: 860, deviceScaleFactor: 1 },
  });
  try {
    const page = await browser.newPage();
    await page.emulateTimezone('UTC');
    // A new Kibana user follows the browser's color scheme, so the public media feature picks the theme.
    await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: theme }]);
    await page.goto(`${base}/login`, { waitUntil: 'networkidle2', timeout: 120000 });
    if (await page.$('input[name="username"]')) { // Not signed in yet (a reused profile may be).
      await page.type('input[name="username"]', 'elastic');
      await page.type('input[name="password"]', env.ELASTIC_PASSWORD);
      await Promise.all([page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 120000 }), page.click('button[type="submit"]')]);
    }
    await page.goto(base + discover, { waitUntil: 'networkidle2', timeout: 120000 });
    await page.waitForSelector('[data-test-subj="discoverQueryHits"], [data-test-subj="unifiedHistogramQueryHits"]', { timeout: 120000 });
    await sleep(6000);
    // Close the usage-collection banner and any tour popovers so they don't cover the chart.
    for (const button of await page.$$('button')) {
      if ((await button.evaluate((el) => el.textContent.trim())) === 'Dismiss') await button.click().catch(() => {});
    }
    await sleep(1500);
    await page.screenshot({ path: out });
    console.log(`Saved ${out}`);
  } finally {
    await browser.close();
  }
})().catch((error) => { console.error(error.message); process.exit(1); });
