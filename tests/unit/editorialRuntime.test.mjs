import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { chromium } from '@playwright/test';

test('registered runtime measures text and binds connectors through rotated groups', async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    const timing = { fps: 30, startFrame: 0, durationFrames: 120, reveal: 'none' };
    const spec = [
      { id: 'group', timing }, { id: 'a', timing }, { id: 'b', timing },
      { id: 'text', timing, text: true, fitText: true, minimumFontSize: 12 },
      { id: 'connector', timing, connector: { from: 'a', to: 'b' } },
    ];
    await page.setContent(`<div id="root" style="position:relative;width:600px;height:400px">
      <div id="group" style="position:absolute;left:40px;top:40px;transform:rotate(30deg) scale(.8);transform-origin:0 0">
        <div id="a" style="width:100px;height:80px;background:red"></div>
      </div>
      <div id="b" style="position:absolute;left:400px;top:250px;width:80px;height:80px"></div>
      <div id="text" style="width:180px;height:70px;font-size:48px;overflow-wrap:break-word">Distribuição: ação e conexão</div>
      <svg id="connector" width="600" height="400" style="position:absolute;left:0;top:0"><polyline/></svg>
      </div><script id="res-editorial-spec" type="application/json">${JSON.stringify(spec)}</script>`);
    await page.addScriptTag({ content: await readFile(new URL('../../backend/app/providers/studios/editorial_runtime.js', import.meta.url), 'utf8') });
    await page.evaluate(() => window.__resEditorialReady);
    const result = await page.evaluate(() => {
      window.__resEditorialApply(1);
      const points = document.querySelector('polyline').points;
      const matrix = document.querySelector('svg').getScreenCTM();
      const point = new DOMPoint(points[0].x, points[0].y).matrixTransform(matrix);
      const box = document.getElementById('a').getBoundingClientRect();
      window.__resEditorialApply(5); window.__resEditorialApply(1);
      return { checks: window.__resEditorialChecks, distance: Math.hypot(point.x - box.x - box.width / 2, point.y - box.y - box.height / 2), display: document.getElementById('a').style.display };
    });
    assert.equal(result.checks.ready, true);
    assert.deepEqual(result.checks.textOverflow, []);
    assert.ok(result.checks.textMeasurements[0].fontSize >= 12);
    assert.ok(result.distance < .01);
    assert.equal(result.display, '');
  } finally { await browser.close(); }
});
