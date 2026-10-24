/** Original, lightweight KLIC voice cues. No downloaded audio or licensed samples. */
export type KlicVoiceCue = 'start' | 'end';

let audioContext: AudioContext | null = null;

/** Call from the user's voice-control gesture so the first cue has no startup delay. */
export function prepareKlicVoiceFeedback(): void {
  if (typeof window === 'undefined') return;
  const Context = window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!Context) return;
  try {
    audioContext ||= new Context();
    if (audioContext.state === 'suspended') void audioContext.resume().catch(() => undefined);
  } catch { /* Sound is optional; voice capture must continue. */ }
}

function emitTone(context: AudioContext, at: number, duration: number, from: number, to: number, volume: number): void {
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(from, at);
  oscillator.frequency.exponentialRampToValueAtTime(to, at + duration);
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.linearRampToValueAtTime(volume, at + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(at);
  oscillator.stop(at + duration + 0.01);
  oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
}

function playCue(cue: KlicVoiceCue, stillCurrent: () => boolean): void {
  prepareKlicVoiceFeedback();
  const context = audioContext;
  if (!context) return;
  const play = () => {
    if (!stillCurrent() || context.state !== 'running') return;
    const at = context.currentTime + 0.008;
    if (cue === 'start') {
      emitTone(context, at, 0.29, 520, 710, 0.042);
      emitTone(context, at + 0.035, 0.23, 780, 960, 0.009);
    } else {
      emitTone(context, at, 0.31, 670, 465, 0.040);
      emitTone(context, at + 0.018, 0.24, 910, 680, 0.008);
    }
  };
  if (context.state === 'running') play();
  else void context.resume().then(play).catch(() => undefined);
}

export function playKlicVoiceStart(stillCurrent: () => boolean = () => true): void { playCue('start', stillCurrent); }
export function playKlicVoiceEnd(stillCurrent: () => boolean = () => true): void { playCue('end', stillCurrent); }

/** One latch per actual voice session; turns and state notifications cannot replay cues. */
export class KlicVoiceFeedbackSession {
  private active = false;
  private revision = 0;

  constructor(private readonly play: (cue: KlicVoiceCue, stillCurrent: () => boolean) => void = playCue) {}

  listeningStarted(): void {
    if (this.active) return;
    this.active = true;
    const revision = ++this.revision;
    this.play('start', () => this.revision === revision);
  }

  listeningEnded(): void {
    if (!this.active) return;
    this.active = false;
    const revision = ++this.revision;
    this.play('end', () => this.revision === revision);
  }
}
