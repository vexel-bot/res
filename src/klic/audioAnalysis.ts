import { SILENT_AUDIO, type KlicAudioSignal } from './hologramDynamics';

/** Derive level and spectral bands exclusively from actual time/frequency samples. */
export function analyseKlicAudio(samples:Uint8Array, bins:Uint8Array, sampleRate:number,
  source:'microphone'|'playback', now:number): KlicAudioSignal {
  let power = 0;
  for (let i = 0; i < samples.length; i++) power += ((samples[i] - 128) / 128) ** 2;
  const hz = sampleRate / Math.max(1, bins.length * 2);
  const band = (from:number, to:number) => {
    const first = Math.max(1, Math.ceil(from / hz)), last = Math.min(bins.length, Math.ceil(to / hz));
    let sum = 0; for (let i = first; i < last; i++) sum += bins[i] / 255;
    return sum / Math.max(1, last - first);
  };
  return { source, level:Math.min(1, Math.sqrt(power / Math.max(1, samples.length)) * (source === 'microphone' ? 12 : 4)),
    low:band(80, 420), high:band(1500, 6000), sampledAt:now };
}

/** Tap the existing HTMLAudioElement; never open another mic or synthesize a beat. */
export function startKlicPlaybackAnalysis(audio:HTMLAudioElement, publish:(signal:KlicAudioSignal) => void): () => void {
  let context:AudioContext | undefined, source:MediaElementAudioSourceNode | undefined, analyser:AnalyserNode | undefined;
  let frame:number | undefined, disposed = false;
  const stop = () => {
    if (disposed) return;
    disposed = true; if (frame !== undefined) cancelAnimationFrame(frame);
    source?.disconnect(); analyser?.disconnect();
    if (context && context.state !== 'closed') void context.close().catch(() => {});
    publish(SILENT_AUDIO);
  };
  try {
    context = new AudioContext();
    const active = context;
    void active.resume().then(() => {
      if (disposed || active.state !== 'running') return;
      // Connect to a running context only, so optional metering cannot mute native playback.
      source = active.createMediaElementSource(audio);
      try {
        analyser = active.createAnalyser(); analyser.fftSize = 1024; analyser.smoothingTimeConstant = .55;
        analyser.connect(active.destination); source.connect(analyser);
      } catch {
        source.connect(active.destination); return;
      }
      const meter = analyser, samples = new Uint8Array(meter.fftSize), bins = new Uint8Array(meter.frequencyBinCount);
      let previous = -Infinity;
      const measure = () => {
        if (disposed) return;
        const now = performance.now();
        if (now - previous >= 32) {
          previous = now;
          if (audio.paused || audio.ended) publish({ ...SILENT_AUDIO, sampledAt:now });
          else {
            meter.getByteTimeDomainData(samples); meter.getByteFrequencyData(bins);
            publish(analyseKlicAudio(samples, bins, active.sampleRate, 'playback', now));
          }
        }
        frame = requestAnimationFrame(measure);
      };
      measure();
    }).catch(() => { /* Native playback remains available without telemetry. */ });
  } catch { publish(SILENT_AUDIO); }
  return stop;
}
