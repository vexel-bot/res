import type { KlicVoiceIdentity, KlicVoicePreference } from './types';

export const KLIC_VOICES = {
  male: {
    label: 'KLIC Male',
    provider: 'google',
    languageCode: 'pt-BR',
    voiceName: 'pt-BR-Chirp3-HD-Charon',
  },
  female: {
    label: 'KLIC Female',
    provider: 'google',
    languageCode: 'pt-BR',
    voiceName: 'pt-BR-Chirp3-HD-Kore',
  },
} as const satisfies Record<KlicVoicePreference, KlicVoiceIdentity>;

export const isKlicVoicePreference = (value: unknown): value is KlicVoicePreference =>
  value === 'male' || value === 'female';

export const klicTtsEnabled = () => process.env.KLIC_GOOGLE_TTS_ENABLED === 'true';
