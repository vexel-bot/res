export type KlicVoiceMode = 'dictation' | 'conversation';

export const transcriptDisposition = (mode: KlicVoiceMode) => mode === 'dictation' ? 'draft' : 'send';

export const shouldRestartVoiceCapture = (mode: KlicVoiceMode | null, muted: boolean) =>
  mode === 'conversation' && !muted;

export function shouldFinishVoiceTurn(input: { elapsedMs: number; silenceMs: number; heardVoice: boolean }) {
  if (!input.heardVoice) return input.elapsedMs > 15_000 ? 'no-speech' : false;
  return input.silenceMs > 1_400 || input.elapsedMs > 60_000 ? 'complete' : false;
}

export const shouldInterruptKlicSpeech = (rms: number, sustainedMs: number) => rms > 0.055 && sustainedMs > 240;
