import type { HologramResonance } from '../hologramModel';

/** Visual parameters adapted from the demo's voiceAnalyzer; no mic, fake cadence or audio ownership. */
export function faceVoiceModulation(time:number,voice:HologramResonance) {
  const listening=voice.listening,speaking=voice.speaking,volume=voice.energy;
  return {volume,
    ribbonWaveSpeed:1.5+listening*(.7+volume*4)+speaking*(2.3+volume*3.5),
    waveAmplitude:.30+volume*.45,
    pulseScale:1+Math.sin(time*1.4)*.02+volume*(listening*.12+speaking*.14),
    rotationSpeed:.132+listening*(.096-.132)+speaking*(.21-.132)};
}
