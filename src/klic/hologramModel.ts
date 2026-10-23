export const KLIC_HOLOGRAM_COLOR = '#6EB8F5';
export const KLIC_HOLOGRAM_RGB = [110 / 255, 184 / 255, 245 / 255] as const;
export type HologramTheme = 'light' | 'dark';
export const HOLOGRAM_PRESENTATION = {
  dark: { shade: 1, opacity: 1, glow: .018 },
  light: { shade: .76, opacity: 1, glow: 0 },
} as const;
export const HOLOGRAM_THEME_DURATION = 400;
export const HOLOGRAM_BANDS = 72;
export const HOLOGRAM_MIN_PARTICLES = 5040;

/** Re-target from the current value, including a second switch mid-transition. */
export class HologramThemeTransition {
  private from: number;
  private to: number;
  private started = -Infinity;
  constructor(theme: HologramTheme) { this.from = this.to = theme === 'light' ? 1 : 0; }
  value(now: number) {
    const x = Math.max(0, Math.min(1, (now - this.started) / HOLOGRAM_THEME_DURATION));
    return this.from + (this.to - this.from) * x * x * (3 - 2 * x);
  }
  set(theme: HologramTheme, now: number) {
    const next = theme === 'light' ? 1 : 0;
    if (next === this.to) return;
    this.from = this.value(now); this.to = next; this.started = now;
  }
  active(now: number) { return this.from !== this.to && now - this.started < HOLOGRAM_THEME_DURATION; }
}

export function hologramPresentation(light: number) {
  const mix = Math.max(0, Math.min(1, Number.isFinite(light) ? light : 0));
  const dark = HOLOGRAM_PRESENTATION.dark, clear = HOLOGRAM_PRESENTATION.light;
  if (mix === 0) return dark;
  if (mix === 1) return clear;
  return { shade: dark.shade + (clear.shade - dark.shade) * mix,
    opacity: dark.opacity + (clear.opacity - dark.opacity) * mix,
    glow: dark.glow + (clear.glow - dark.glow) * mix };
}

export function hologramBudget(cores = 4, memory = 4, saveData = false) {
  if (saveData || cores <= 2 || memory <= 2) return HOLOGRAM_MIN_PARTICLES;
  return cores >= 8 && memory >= 8 ? 10800 : 7200;
}

/** Low-discrepancy prefixes remain spherical when draw count is reduced. */
export function hologramParticles(count: number): Float32Array {
  const total = Math.max(HOLOGRAM_MIN_PARTICLES, Math.min(12000, Math.floor(Number.isFinite(count) ? count : 7200)));
  const points = new Float32Array(total * 5);
  const fract = (value: number) => value - Math.floor(value);
  for (let i = 0; i < total; i++) {
    const seed = fract((i + 1) * .4142135623730951);
    const band = i % HOLOGRAM_BANDS;
    const longitude = fract(Math.floor(i / HOLOGRAM_BANDS) * .61803398875 + band * .1375035) * Math.PI * 2;
    const latitude = -.985 + (band + .5) / HOLOGRAM_BANDS * 1.97;
    const y = Math.max(-.995, Math.min(.995, latitude + (.024 * Math.sin(longitude * 3 + band * .13)
      + .012 * Math.sin(longitude * 5 - band * .19)) * (1 - latitude * latitude)));
    const radius = seed < .18 ? .65 + .29 * Math.cbrt(seed / .18) : .982 + .018 * fract(i * .61803398875);
    const ring = Math.sqrt(1 - y * y) * radius;
    points.set([Math.cos(longitude) * ring, y * radius, Math.sin(longitude) * ring, seed, .6 + fract(i * .73205080757) * .8], i * 5);
  }
  return points;
}

export type HologramResonance = { listening: number; speaking: number; energy: number; low: number; high: number };
export const QUIET_RESONANCE: HologramResonance = { listening:0, speaking:0, energy:0, low:0, high:0 };
export type HologramProjection = { x:number; y:number; z:number; size:number; opacity:number; front:number; cameraX:number; cameraY:number };
export type HologramPose = { breath:number; cy:number;sy:number;cx:number;sx:number;cz:number;sz:number };
export function hologramPose(time:number,result={} as HologramPose) {
  const angle=time*.025+.03*Math.sin(time*.17),tilt=-.14+.055*Math.sin(time*.23),roll=.04*Math.sin(time*.19);
  result.breath=1+.03*Math.sin(time*1.4);
  result.cy=Math.cos(angle);result.sy=Math.sin(angle);result.cx=Math.cos(tilt);result.sx=Math.sin(tilt);result.cz=Math.cos(roll);result.sz=Math.sin(roll);
  return result;
}

export function hologramPointColor(front:number, shade:number): number[] {
  const smooth = (a:number,b:number,x:number) => { const t=Math.max(0,Math.min(1,(x-a)/(b-a)));return t*t*(3-2*t); };
  const middle=smooth(.05,.55,front), near=smooth(.65,1,front)*.78;
  return [45,115,195].map((rear,axis)=>{
    const base=rear*(1-middle)+KLIC_HOLOGRAM_RGB[axis]*255*middle;
    const sky=[165+15*front,215+10*front,255][axis];
    return Math.min(255,Math.round((base*(1-near)+sky*near)*shade));
  });
}

/** Shared procedural rest shape for the native Canvas face and local force model. */
export function projectHologramPoint(data: Float32Array, index: number, time: number, voice = QUIET_RESONANCE,
  result = {} as HologramProjection, pose=hologramPose(time), cachedLongitude?:number, cachedRadius?:number): HologramProjection {
  const offset = index * 5;
  let x = data[offset], y = data[offset + 1], z = data[offset + 2];
  const seed = data[offset + 3], size = data[offset + 4];
  const longitude = cachedLongitude ?? Math.atan2(z, x);
  const radius = cachedRadius ?? Math.hypot(x, y, z);
  const equator = 1 - y * y;
  const wave = .014 * Math.sin(longitude * 3 + y * 8 - time * .5) + .007 * Math.sin(longitude * 5 - time * .31 + seed * 3);
  const listenWave = voice.listening ? Math.sin((1 - Math.abs(y)) * 19 - time * (2.2 + voice.low)) * voice.listening * (.003 + voice.energy * .022) : 0;
  const vibration = voice.listening && voice.energy ? Math.sin(time * 113.097 + seed * 6.283) * voice.listening * voice.energy * .0018 * (.4 + voice.high) : 0;
  const speaking = voice.speaking * voice.energy;
  const resonantWave = speaking ? wave * (1 - .35 * speaking) + Math.sin(radius * 12 - time * 4.3 + longitude * 2) * speaking * .00735 * equator : wave;
  const scale = pose.breath + resonantWave * (1 + .4 * speaking) + listenWave + vibration;
  const vertical = (.016 * Math.sin(longitude * 2 + time * .27 + y * 5) + listenWave * .3) * equator;
  x *= scale; z *= scale; y = y * pose.breath + vertical;
  const rx = pose.cy * x + pose.sy * z, rz = -pose.sy * x + pose.cy * z;
  const ry = pose.cx * y - pose.sx * rz;
  z = pose.sx * y + pose.cx * rz;
  const cx = pose.cz * rx - pose.sz * ry, cy = pose.sz * rx + pose.cz * ry;
  const perspective = 2.65 / (3.7 - z), front = Math.max(0, Math.min(1, (z + 1.1) / 2.2));
  const depth = Math.max(0, Math.min(1, (z + .2) / .9)), near = depth * depth * (3 - 2 * depth);
  result.x = cx * perspective; result.y = cy * perspective; result.z = z; result.cameraX = cx; result.cameraY = cy;
  result.front = front;
  result.size = Math.max(.6, Math.min(1.4 + voice.speaking * voice.energy * .1, size * (.85 + .15 * front) + voice.speaking * voice.energy * .14));
  result.opacity = (.20 + .15 * seed) * (1 - near) + (.85 + .13 * seed) * near;
  return result;
}

export type HologramFrame = { time: number; light: number; delta?: number; reduced?: boolean };
type LoopHost = { now: () => number; request: (callback: (now: number) => void) => number; cancel: (id: number) => void; draw: (frame: HologramFrame) => void };

/** One RAF, a continuous phase clock, and no React updates inside the loop. */
export class HologramLoop {
  private frame?: number;
  private previous?: number;
  private time = 2.4;
  private visible = false;
  private reduced = false;
  private disposed = false;
  readonly presentation: HologramThemeTransition;
  constructor(private host: LoopHost, theme: HologramTheme) { this.presentation = new HologramThemeTransition(theme); }
  private schedule() {
    if (!this.disposed && this.visible && this.frame === undefined) this.frame = this.host.request(this.tick);
  }
  private tick = (now: number) => {
    this.frame = undefined;
    if (this.disposed || !this.visible) return;
    const delta = this.previous === undefined ? 0 : Math.max(0, Math.min(.05, (now - this.previous) / 1000));
    if (!this.reduced) this.time += delta;
    this.previous = now;
    this.host.draw({ time:this.time, light:this.presentation.value(now), delta, reduced:this.reduced });
    if (!this.reduced || this.presentation.active(now)) this.schedule();
  };
  setTheme(theme: HologramTheme) { this.presentation.set(theme, this.host.now()); this.schedule(); }
  setVisible(visible: boolean) {
    this.visible = visible; this.previous = undefined;
    if (visible) this.schedule();
    else if (this.frame !== undefined) { this.host.cancel(this.frame); this.frame = undefined; }
  }
  setReducedMotion(reduced: boolean) { this.reduced = reduced; this.previous = undefined; this.schedule(); }
  invalidate() { this.schedule(); }
  dispose() { this.disposed = true; if (this.frame !== undefined) this.host.cancel(this.frame); this.frame = undefined; }
}
