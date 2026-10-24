import { projectHologramPoint, QUIET_RESONANCE, type HologramProjection, type HologramResonance } from './hologramModel';
import type { KlicPlasmaState } from './plasmaState';

export type KlicAudioSignal = { source:'none'|'microphone'|'playback'; level:number; low:number; high:number; sampledAt:number };
export const SILENT_AUDIO: KlicAudioSignal = { source:'none', level:0, low:0, high:0, sampledAt:0 };
const clamp = (value:number, max = 1) => Math.max(0, Math.min(max, Number.isFinite(value) ? value : 0));

/** No random/synthetic audio: silence, stale telemetry and native TTS all decay to zero. */
export class HologramCommunication {
  readonly value: HologramResonance = { ...QUIET_RESONANCE };
  step(state: KlicPlasmaState, signal: KlicAudioSignal, delta:number, now:number, reduced = false) {
    const listening = state === 'listening' ? 1 : 0, speaking = state === 'speaking' ? 1 : 0;
    const actual = now - signal.sampledAt >= 0 && now - signal.sampledAt < 250
      && ((listening && signal.source === 'microphone') || (speaking && signal.source === 'playback'));
    const target = { listening, speaking, energy:actual ? clamp(signal.level) : 0,
      low:actual ? clamp(signal.low) : 0, high:actual ? clamp(signal.high) : 0 };
    const blend = reduced ? 1 : 1 - Math.exp(-Math.max(0, delta) * 16);
    for (const key of Object.keys(target) as Array<keyof HologramResonance>) this.value[key] += (target[key] - this.value[key]) * blend;
    return this.value;
  }
}

export type HologramPointer = { active:boolean; x:number; y:number; vx:number; vy:number };
export const REST_POINTER: HologramPointer = { active:false, x:0, y:0, vx:0, vy:0 };

/** Camera-space spring offsets follow the continuously moving procedural rest shape. */
export class HologramPhysics {
  readonly offsets: Float32Array;
  readonly velocities: Float32Array;
  private moving = false;
  private projection = {} as HologramProjection;
  constructor(count:number) { this.offsets = new Float32Array(count * 3); this.velocities = new Float32Array(count * 3); }
  reset() { this.offsets.fill(0); this.velocities.fill(0); this.moving = false; }
  step(points:Float32Array, time:number, delta:number, voice:HologramResonance, pointer:HologramPointer, aspect = 1) {
    if (!pointer.active && !this.moving) return false;
    const dt = Math.min(.05, clamp(delta, .05));
    if (!dt) return false;
    const steps = Math.max(1, Math.ceil(dt * 120)), h = dt / steps, damping = Math.pow(.9, h * 60);
    let energy = 0;
    for (let i = 0; i < this.offsets.length / 3; i++) {
      const k = i * 3;
      const p = projectHologramPoint(points, i, time, voice, this.projection);
      const perspective = 2.65 / (3.7 - p.z);
      const dx = p.cameraX + this.offsets[k] - pointer.x * aspect / perspective;
      const dy = p.cameraY + this.offsets[k + 1] - pointer.y / perspective;
      const distance = Math.hypot(dx, dy), falloff = Math.max(0, 1 - distance / .43) ** 2;
      const force = pointer.active ? Math.min(22, .12 / (distance * distance + .012)) * falloff * (.25 + .75 * p.front) : 0;
      const normalX = distance > .001 ? dx / distance : Math.cos(i * 2.4), normalY = distance > .001 ? dy / distance : Math.sin(i * 2.4);
      for (let step = 0; step < steps; step++) for (let axis = 0; axis < 3; axis++) {
        const acceleration = axis === 0 ? normalX * force + clampSigned(pointer.vx, 12) * falloff * (pointer.active ? .9 : 0)
          : axis === 1 ? normalY * force + clampSigned(pointer.vy, 12) * falloff * (pointer.active ? .9 : 0) : force * .22;
        const index = k + axis;
        this.velocities[index] = clampSigned((this.velocities[index] + (acceleration - 65 * this.offsets[index]) * h) * damping, 2.2);
        this.offsets[index] += this.velocities[index] * h;
        if (Math.abs(this.offsets[index]) > .24) { this.offsets[index] = clampSigned(this.offsets[index], .24); this.velocities[index] *= .35; }
        energy = Math.max(energy, Math.abs(this.offsets[index]), Math.abs(this.velocities[index]));
      }
    }
    this.moving = energy > .00004;
    if (!this.moving) this.reset();
    return true;
  }
}
const clampSigned = (value:number, max:number) => Math.max(-max, Math.min(max, Number.isFinite(value) ? value : 0));
