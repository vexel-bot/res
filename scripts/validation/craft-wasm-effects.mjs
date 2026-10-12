// Actual EffectCraft commands, timed legacy migration, alpha and native reopening.
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:3018', { waitUntil: 'domcontentloaded', timeout: 120000 });
  const result = await page.evaluate(async () => {
    const { CraftWorker } = await import('/src/studios/craft/craftWorker.ts');
    const worker = new CraftWorker('effectcraft', crypto.randomUUID(), 1);
    const digest = async data => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', data)), b => b.toString(16).padStart(2, '0')).join('');
    const request = async (method, params = {}) => {
      const response = JSON.parse(await worker.call('request', JSON.stringify({ protocolVersion: 1,
        requestId: crypto.randomUUID(), engine: 'effectcraft', method, params })));
      if (response.error) throw new Error(response.error.message);
      return response.result;
    };
    const execute = (command, params) => request('engine.execute', { command, params });
    const preview = time => worker.call('preview', time, 0);
    const pixel = async (png, x, y) => {
      const bitmap = await createImageBitmap(new Blob([png], { type: 'image/png' }));
      try {
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width; canvas.height = bitmap.height;
        const context = canvas.getContext('2d');
        context.drawImage(bitmap, 0, 0);
        return Array.from(context.getImageData(x, y, 1, 1).data);
      } finally { bitmap.close(); }
    };
    try {
      await worker.initialize();
      await request('project.new', { width: 320, height: 320, fps: 10, durationMs: 200,
        legacyDocument: { composition: { pages: [{ width: 320, height: 320, background: '#00000000', layers: [
          { id: 'child', kind: 'shape', x: 4, y: 0, width: 4, height: 4, opacity: 0.5, properties: { fill: '#ff0000' } },
          { id: 'group', kind: 'group', x: 20, y: 20, width: 16, height: 16, rotation: 90, opacity: 0.5, properties: {} },
        ] }] } },
        legacyMotionGraph: { frameRate: { numerator: 10, denominator: 1 }, durationFrames: 2,
          nodes: [{ nodeId: 'g', targetLayerId: 'group', transformOriginX: 0, transformOriginY: 0 },
            { nodeId: 'c', targetLayerId: 'child', parentNodeId: 'g' }],
          tracks: [{ targetLayerId: 'group', property: 'position_x', keyframes: [{ frame: 0, value: 0 }, { frame: 1, value: 8 }] },
            { targetLayerId: 'group', property: 'opacity', keyframes: [{ frame: 0, value: 0.5 }, { frame: 1, value: 1 }] }],
        } });
      const groupFirst = await preview(0), groupLast = await preview(0.1);
      if (JSON.stringify(await pixel(groupFirst, 17, 25)) !== '[255,0,0,64]' ||
          JSON.stringify(await pixel(groupLast, 25, 25)) !== '[255,0,0,128]') throw new Error('Group geometry/alpha changed');
      await worker.call('open', await worker.call('save'));
      if (await digest(groupFirst) !== await digest(await preview(0)) ||
          await digest(groupLast) !== await digest(await preview(0.1))) throw new Error('Group reopening changed pixels');
      await request('project.new', { width: 16, height: 16, fps: 10, durationMs: 1000,
        legacyDocument: { composition: { pages: [{ width: 16, height: 16, layers: [{
          id: 'square', kind: 'shape', name: 'Square', x: 0, y: 0, width: 8, height: 8,
          properties: { fill: '#ff0000', editorialTiming: { fps: 10, startFrame: 2, durationFrames: 4 } },
        }] }] } } });
      const absent = await digest(await preview(0));
      const visible = await digest(await preview(0.2));
      if (absent === visible || absent !== await digest(await preview(0.6))) throw new Error('Migration lost authored layer timing');
      await worker.call('open', await worker.call('save'));
      if (visible !== await digest(await preview(0.2))) throw new Error('Reopening lost authored layer timing');
      const state = await request('project.inspect');
      await execute('edit.clear', { layers: state.inspection.layers.map(layer => Number(layer.id)) });
      await execute('layer.newSolid', { color: '#ff0000', width: 8, height: 8 });
      const rgba = await preview(0);
      const corner = await pixel(rgba, 0, 0);
      const center = await pixel(rgba, 8, 8);
      await worker.call('open', await worker.call('save'));
      if (await digest(rgba) !== await digest(await preview(0))) throw new Error('Reopening changed transparency');
      return { engine: 'effectcraft', hierarchy: true, pivot: true, inheritedAlpha: true,
        groupFrameSha256: [await digest(groupFirst), await digest(groupLast)],
        timing: true, editClear: true, alpha: true, reopen: true, corner, center };
    } finally { worker.close(); }
  });
  assert.equal(result.corner[3], 0);
  assert.deepEqual(result.center, [255, 0, 0, 255]);
  const native = JSON.parse(await readFile(resolve('.codex-runtime/craft/hierarchy-acceptance-results.json'), 'utf8'));
  assert.deepEqual(result.groupFrameSha256, native.frameSha256, 'WASM hierarchy pixels differ from the native API');
  console.log(JSON.stringify(result));
  await writeFile(resolve('.codex-runtime/craft/wasm-effects-results.json'), JSON.stringify(result, null, 2));
} finally { await browser.close(); }
