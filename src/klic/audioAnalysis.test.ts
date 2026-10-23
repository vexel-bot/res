import test from 'node:test';
import assert from 'node:assert/strict';
import { analyseKlicAudio, startKlicPlaybackAnalysis } from './audioAnalysis';
import type { KlicAudioSignal } from './hologramDynamics';

test('actual sample silence produces no level; RMS and frequency bands track the input', () => {
  const silence = new Uint8Array(1024).fill(128), bins = new Uint8Array(512);
  assert.equal(analyseKlicAudio(silence, bins, 48000, 'microphone', 10).level, 0);
  const wave = Uint8Array.from({length:1024}, (_, i) => 128 + Math.round(16 * Math.sin(i * Math.PI / 12)));
  bins.fill(200, 2, 9);
  const mic = analyseKlicAudio(wave, bins, 48000, 'microphone', 100);
  const playback = analyseKlicAudio(wave, bins, 48000, 'playback', 100);
  assert.ok(mic.level > .7 && playback.level > .2 && playback.level < mic.level);
  assert.ok(mic.low > .5 && mic.high === 0);
  assert.equal(playback.source, 'playback'); assert.equal(playback.sampledAt, 100);
});

test('playback metering taps the existing element, routes audio, respects pauses and releases its graph', async () => {
  const names = ['AudioContext', 'performance', 'requestAnimationFrame', 'cancelAnimationFrame'] as const;
  const originals = new Map(names.map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  let now = 0, id = 0, sources = 0, closed = 0, disconnected = 0;
  const frames = new Map<number, () => void>(), signals:KlicAudioSignal[] = [];
  const audioState = { paused:false, ended:false }, audio = audioState as HTMLAudioElement;
  class Context {
    state = 'running'; sampleRate = 48000; destination = {};
    async resume() {} async close() { this.state = 'closed'; closed++; }
    createMediaElementSource(element:HTMLAudioElement) { assert.equal(element, audio); sources++; return {connect() {},disconnect() { disconnected++; }}; }
    createAnalyser() { return {fftSize:1024,frequencyBinCount:512,smoothingTimeConstant:0,connect() {},disconnect() {disconnected++;},
      getByteTimeDomainData(out:Uint8Array) {out.fill(144);}, getByteFrequencyData(out:Uint8Array) {out.fill(100);} }; }
  }
  const values = { AudioContext:Context, performance:{now:()=>now}, requestAnimationFrame:(callback:()=>void)=>{frames.set(++id,callback);return id;}, cancelAnimationFrame:(key:number)=>frames.delete(key) };
  for (const name of names) Object.defineProperty(globalThis,name,{configurable:true,value:values[name]});
  try {
    const stop = startKlicPlaybackAnalysis(audio, signal=>signals.push(signal));
    await Promise.resolve(); await Promise.resolve();
    assert.equal(sources, 1); assert.ok(signals.at(-1)!.level > 0); assert.equal(frames.size, 1);
    audioState.paused = true; now = 64; const callbacks = [...frames.values()]; frames.clear(); callbacks.forEach(callback=>callback());
    assert.equal(signals.at(-1)!.level, 0);
    stop(); stop(); assert.equal(frames.size, 0); assert.equal(closed, 1); assert.equal(disconnected, 2);
    assert.equal(signals.at(-1)!.source, 'none');
  } finally {
    for (const name of names) { const original = originals.get(name); if (original) Object.defineProperty(globalThis,name,original); else Reflect.deleteProperty(globalThis,name); }
  }
});
