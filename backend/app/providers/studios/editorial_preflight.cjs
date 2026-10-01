// Inspect only the registered, generated composition before frame capture.
const { createRequire } = require('node:module');
const { pathToFileURL, fileURLToPath } = require('node:url');
const path = require('node:path');
const fs = require('node:fs');
const [entry, executablePath, project] = process.argv.slice(2);
const puppeteer = createRequire(path.resolve(entry))('puppeteer-core');
let phase = 'launch';
(async () => {
  const browser = await puppeteer.launch({ executablePath, headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--no-first-run', '--disable-background-timer-throttling',
      '--disable-backgrounding-occluded-windows', '--disable-renderer-backgrounding'], timeout: 30000 });
  try {
    phase = 'new-page';
    const page = await browser.newPage();
    phase = 'interception';
    await page.setRequestInterception(true);
    page.on('request', req => {
      let allowed = req.url().startsWith('data:');
      if (req.url().startsWith('file:')) {
        try {
          const relative = path.relative(fs.realpathSync(project), fs.realpathSync(fileURLToPath(req.url())));
          allowed = !relative.startsWith('..') && !path.isAbsolute(relative);
        } catch { allowed = false; }
      }
      allowed ? req.continue() : req.abort();
    });
    phase = 'navigation';
    await page.goto(pathToFileURL(path.join(project, 'index.html')).href, {waitUntil: 'load'});
    phase = 'font-and-text-checks';
    const checks = await page.evaluate(async () => {
      await Promise.race([window.__resEditorialReady, new Promise((_, reject) => setTimeout(() => reject(new Error('editorial_ready_timeout')), 15000))]);
      const spec = JSON.parse(document.getElementById('res-editorial-spec').textContent);
      const overflow = new Set();
      const overflowMeasurements = new Map();
      // Check every scene and every declared keyframe, including hidden descendants.
      const motion = JSON.parse(document.getElementById('clicko-motion-spec').textContent);
      const fps = motion.frameRate.numerator / motion.frameRate.denominator;
      const frames = new Set(spec.map(s => s.timing.startFrame + Math.min(s.timing.durationFrames - 1, s.timing.revealFrames || 1)));
      spec.forEach(s => {
        frames.add(s.timing.startFrame);
        frames.add(s.timing.startFrame + s.timing.durationFrames - 1);
      });
      spec.forEach(s => (s.auditFrames || []).forEach(frame => frames.add(frame)));
      spec.forEach(s => (s.textSpans || []).forEach(span => {
        if (span.startFrame === null || span.startFrame === undefined) return;
        const start = s.timing.startFrame + span.startFrame;
        const end = start + span.durationFrames - 1;
        frames.add(start);
        frames.add(Math.floor((start + end) / 2));
        frames.add(end);
      }));
      motion.tracks.forEach(t => t.keyframes.forEach(k => frames.add(k.frame)));
      const handoffs = spec.filter(s => s.match);
      handoffs.forEach(s => {
        frames.add(Math.max(0, s.match.startFrame - 1));
        frames.add(s.match.startFrame);
        frames.add(Math.floor((s.match.startFrame + s.match.endFrameExclusive) / 2));
        frames.add(s.match.endFrameExclusive);
      });
      for (const frame of frames) {
        window.__clickoMotionApply(frame / fps);
        window.__resEditorialApply(frame / fps);
        for (const item of spec) {
          const el = document.getElementById(item.id);
          if (!item.text || !el || !el.getClientRects().length) continue;
          if (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1) {
            overflow.add(item.id);
            const style = getComputedStyle(el);
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
            const measured = {
              layerId: item.id, frame,
              boxWidth: el.clientWidth, boxHeight: el.clientHeight,
              contentWidth: el.scrollWidth, contentHeight: el.scrollHeight,
              unwrappedTextWidth: context.measureText(el.textContent).width,
              fontFamily: style.fontFamily, fontSize: style.fontSize, fontWeight: style.fontWeight,
            };
            const previous = overflowMeasurements.get(item.id);
            if (!previous || measured.contentHeight > previous.contentHeight ||
                measured.unwrappedTextWidth > previous.unwrappedTextWidth) overflowMeasurements.set(item.id, measured);
          }
        }
      }
      const handoffErrors = new Set();
      const ordered = [...frames].sort((a,b)=>a-b);
      const geometrySamples = [];
      for (const frame of ordered) {
        window.__clickoMotionApply(frame / fps);
        window.__resEditorialApply(frame / fps);
        geometrySamples.push({frame, elements: window.__resEditorialObserve(frame)});
      }
      // The same seek runtime drives preview and export. Exercise reverse seeks
      // too: a temporary overlay must return to its declared parent afterwards.
      if (handoffs.length) for (const frame of [...ordered, ...ordered.toReversed()]) {
        window.__clickoMotionApply(frame / fps);
        window.__resEditorialApply(frame / fps);
        for (const item of handoffs) {
          const el = document.getElementById(item.id);
          const parent = document.getElementById(item.match.parentLayerId);
          const prior = document.getElementById(item.match.previousLayerId);
          const active = frame >= item.match.startFrame && frame < item.match.endFrameExclusive;
          if (el.parentElement !== (active ? parent.parentElement : parent)) handoffErrors.add(item.id + ':parent');
          if (active && prior.style.display !== 'none') handoffErrors.add(item.id + ':duplicate');
        }
      }
      return {...window.__resEditorialChecks,
        errors: [...window.__resEditorialChecks.errors, ...handoffErrors],
        textOverflow: [...overflow], textOverflowMeasurements: [...overflowMeasurements.values()], sampledFrames: ordered,
        geometrySchemaVersion: 'studio.rendered-geometry.v1', geometrySamples,
        handoffChecks: { count: handoffs.length, reverseSeek: handoffs.length > 0, errors: [...handoffErrors] }};
    });
    process.stdout.write(JSON.stringify(checks));
    if (!checks.ready || checks.errors.length || checks.textOverflow.length) process.exitCode = 2;
  } finally { await browser.close(); }
})().catch(error => { process.stderr.write(phase + ': ' + (error.stack || String(error))); process.exitCode = 1; });
