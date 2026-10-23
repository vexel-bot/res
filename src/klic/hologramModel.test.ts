import test from 'node:test';
import assert from 'node:assert/strict';
import { HologramLoop, HologramThemeTransition, HOLOGRAM_PRESENTATION, HOLOGRAM_THEME_DURATION,
  KLIC_HOLOGRAM_COLOR, KLIC_HOLOGRAM_RGB, hologramBudget, hologramParticles, hologramPresentation,
  projectHologramPoint, type HologramFrame } from './hologramModel';

function clock() {
  let now = 0, id = 0;
  const pending = new Map<number, (time: number) => void>();
  const frames: HologramFrame[] = [];
  const loop = new HologramLoop({ now: () => now,
    request: callback => { pending.set(++id, callback); return id; },
    cancel: key => { pending.delete(key); }, draw: frame => { frames.push(frame); } }, 'dark');
  return { loop, frames, pending, step(time: number) {
    now = time; const work = [...pending.values()]; pending.clear(); work.forEach(callback => callback(time));
  } };
}

test('official blue stays the shared source; presentation alone adapts to theme', () => {
  assert.equal(KLIC_HOLOGRAM_COLOR, '#6EB8F5');
  assert.deepEqual(KLIC_HOLOGRAM_RGB.map(channel => Math.round(channel * 255)), [110, 184, 245]);
  assert.deepEqual(hologramPresentation(0), HOLOGRAM_PRESENTATION.dark);
  assert.deepEqual(hologramPresentation(1), HOLOGRAM_PRESENTATION.light);
  const middle = hologramPresentation(.5);
  assert.equal(middle.opacity, 1);
  assert.ok(HOLOGRAM_PRESENTATION.light.shade < HOLOGRAM_PRESENTATION.dark.shade);
  assert.ok(HOLOGRAM_PRESENTATION.light.glow < HOLOGRAM_PRESENTATION.dark.glow);
  assert.deepEqual(hologramPresentation(NaN), HOLOGRAM_PRESENTATION.dark);
});

test('theme interpolation lasts 400ms and reverses seamlessly mid-transition', () => {
  const theme = new HologramThemeTransition('dark');
  theme.set('light', 100);
  assert.equal(theme.value(100), 0); assert.equal(theme.value(300), .5);
  theme.set('dark', 300);
  assert.equal(theme.value(300), .5); assert.equal(theme.value(500), .25);
  assert.equal(theme.value(700), 0); assert.equal(theme.active(700), false);
  theme.set('light', 800); theme.set('light', 900);
  assert.equal(theme.value(800 + HOLOGRAM_THEME_DURATION), 1);
});

test('device budgets are bounded and sphere prefixes preserve all hemispheres', () => {
  assert.equal(hologramBudget(2, 8), 5040); assert.equal(hologramBudget(8, 2), 5040);
  assert.equal(hologramBudget(16, 16, true), 5040);
  assert.equal(hologramBudget(), 7200); assert.equal(hologramBudget(8, 8), 10800);
  const points = hologramParticles(10800);
  assert.deepEqual(points, hologramParticles(10800));
  for (const count of [5040, 7200, 10800]) {
    const sum = [0, 0, 0], low = [1, 1, 1], high = [-1, -1, -1];
    let interior = 0;
    for (let i = 0; i < count; i++) {
      const [x, y, z, seed, size] = points.subarray(i * 5, i * 5 + 5);
      const radius = Math.hypot(x, y, z);
      assert.ok(radius >= .35 && radius <= 1.003);
      assert.ok(seed >= 0 && seed <= 1 && size >= .5999 && size <= 1.4001);
      if (radius < .95) interior++;
      for (const [axis, value] of [x, y, z].entries()) {
        sum[axis] += value; low[axis] = Math.min(low[axis], value); high[axis] = Math.max(high[axis], value);
      }
    }
    assert.ok(interior / count > .15 && interior / count < .22);
    for (let axis = 0; axis < 3; axis++) { assert.ok(Math.abs(sum[axis] / count) < .02); assert.ok(low[axis] < -.95 && high[axis] > .95); }
  }
  assert.equal(hologramParticles(-1).length, 5040 * 5);
  assert.equal(hologramParticles(NaN).length, 7200 * 5);
  assert.equal(hologramParticles(999999).length, 12000 * 5);
});

test('procedural waves stay framed and continuous rather than dispersing the sphere', () => {
  const points = hologramParticles(3200);
  let moved = 0;
  for (let i = 0; i < 3200; i += 5) for (const time of [0, 20, 200, 20000]) {
    const a = projectHologramPoint(points, i, time), b = projectHologramPoint(points, i, time + .016);
    assert.ok(Math.abs(a.x) < .85 && Math.abs(a.y) < .85);
    assert.ok(a.opacity > 0 && a.opacity <= 1 && a.size > 0);
    assert.ok(Math.hypot(a.x - b.x, a.y - b.y) < .005);
    if (a.x !== b.x || a.y !== b.y) moved++;
  }
  assert.ok(moved > 2000);
});

test('one RAF and a preserved phase through theme switches and hidden periods', () => {
  const { loop, frames, pending, step } = clock();
  loop.setVisible(true); loop.invalidate(); loop.setTheme('dark');
  assert.equal(pending.size, 1);
  step(0); step(16); const start = frames.at(-1)!.time;
  loop.setTheme('light'); step(32); step(216);
  assert.ok(frames.at(-1)!.time > start); assert.equal(frames.at(-1)!.light, .5);
  loop.setVisible(false); assert.equal(pending.size, 0); const paused = frames.at(-1)!.time;
  step(10000); loop.setVisible(true); step(10016);
  assert.equal(frames.at(-1)!.time, paused); assert.equal(frames.at(-1)!.light, 1);
  step(10032); assert.ok(frames.at(-1)!.time > paused);
  loop.dispose(); assert.equal(pending.size, 0);
  loop.invalidate(); loop.setTheme('dark'); loop.setVisible(true); assert.equal(pending.size, 0);
});

test('reduced motion freezes geometry, finishes the theme fade and stops RAF', () => {
  const { loop, frames, pending, step } = clock();
  loop.setReducedMotion(true); loop.setVisible(true); step(0);
  assert.equal(pending.size, 0); const phase = frames[0].time;
  loop.setTheme('light'); step(0); step(200); step(400);
  assert.deepEqual(frames.map(frame => frame.time), [phase, phase, phase, phase]);
  assert.deepEqual(frames.map(frame => frame.light), [0, 0, .5, 1]);
  assert.equal(pending.size, 0);
  loop.setReducedMotion(false); step(416); step(432);
  assert.ok(frames.at(-1)!.time > phase); loop.dispose();
});
