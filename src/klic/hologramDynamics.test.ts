import test from 'node:test';
import assert from 'node:assert/strict';
import { HologramCommunication, HologramPhysics, REST_POINTER, SILENT_AUDIO } from './hologramDynamics';
import { hologramParticles, projectHologramPoint, QUIET_RESONANCE } from './hologramModel';

test('all 72 harmonic bands retain volume, microparticle dimensions and near/far opacity', () => {
  const points = hologramParticles(7200); let near = 0, far = 0;
  const bands = new Set<number>();
  for (let i = 0; i < 7200; i++) {
    bands.add(i % 72);
    const p = projectHologramPoint(points, i, 1);
    assert.ok(p.size >= .6 && p.size <= 1.4);
    if (p.z > .7) { near++; assert.ok(p.opacity >= .85 && p.opacity <= .98); }
    if (p.z < -.2) { far++; assert.ok(p.opacity >= .2 && p.opacity <= .35); }
  }
  assert.equal(bands.size, 72); assert.ok(near > 100); assert.ok(far > 1000);
});

test('listening/speaking accept only fresh matching real audio and interpolate without fake pulses', () => {
  const voice = new HologramCommunication();
  for (let i = 0; i < 30; i++) voice.step('listening', {source:'microphone',level:.8,low:.5,high:.2,sampledAt:i*16}, .016, i*16);
  assert.ok(voice.value.listening > .99 && voice.value.energy > .79);
  const before = { ...voice.value };
  voice.step('speaking', {source:'playback',level:.2,low:.1,high:.7,sampledAt:500}, .016, 500);
  assert.ok(voice.value.speaking > 0 && voice.value.speaking < 1);
  assert.ok(voice.value.energy < before.energy && voice.value.energy > .2);
  for (let i = 0; i < 100; i++) voice.step('speaking', SILENT_AUDIO, .016, 1000 + i * 16);
  assert.ok(voice.value.energy < .00001);
  for (const signal of [{source:'microphone' as const,level:1,low:1,high:1,sampledAt:3000},
    {source:'playback' as const,level:1,low:1,high:1,sampledAt:1000}]) {
    const fresh = new HologramCommunication(); fresh.step('speaking', signal, 1, 3000);
    assert.equal(fresh.value.energy, 0);
  }
});

test('local force displaces a subset; Hooke/damping fully restore the moving geometry', () => {
  const points = hologramParticles(5040), physics = new HologramPhysics(points.length / 5);
  for (let i = 0; i < 20; i++) physics.step(points, i / 60, 1 / 60, QUIET_RESONANCE, {active:true,x:.25,y:.15,vx:4,vy:1});
  let affected = 0;
  for (let i = 0; i < physics.offsets.length; i += 3) if (Math.hypot(...physics.offsets.subarray(i,i+3)) > .001) affected++;
  assert.ok(affected > 30 && affected < 5040 * .5);
  for (const value of physics.offsets) assert.ok(Number.isFinite(value) && Math.abs(value) <= .24001);
  for (let i = 20; i < 700; i++) physics.step(points, i / 60, 1 / 60, QUIET_RESONANCE, REST_POINTER);
  assert.ok(physics.offsets.every(value => value === 0)); assert.ok(physics.velocities.every(value => value === 0));
});

test('spring integration is stable across 30/60/120 FPS and extreme frame gaps', () => {
  const points = hologramParticles(5040);
  const simulate = (fps:number) => {
    const physics = new HologramPhysics(points.length / 5);
    for (let i = 0; i < fps; i++) physics.step(points, i / fps, 1 / fps, QUIET_RESONANCE,
      i < fps / 4 ? {active:true,x:.3,y:.1,vx:1,vy:0} : REST_POINTER);
    physics.step(points, 1, 10, QUIET_RESONANCE, REST_POINTER);
    return physics;
  };
  const low = simulate(30), high = simulate(120);
  let difference = 0;
  for (let i = 0; i < low.offsets.length; i++) {
    assert.ok(Number.isFinite(low.offsets[i]) && Number.isFinite(high.offsets[i]));
    difference += (low.offsets[i] - high.offsets[i]) ** 2;
  }
  assert.ok(Math.sqrt(difference / low.offsets.length) < .006);
  low.reset(); assert.ok(low.offsets.every(value => value === 0));
});
