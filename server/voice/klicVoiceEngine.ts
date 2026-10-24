import { KLIC_VOICES } from './config';
import { GoogleCloudTtsProvider } from './providers/googleCloudTtsProvider';
import type { KlicVoicePreference, TtsProvider, TtsSynthesisResult } from './types';

const providers: Record<string, TtsProvider> = {
  google: new GoogleCloudTtsProvider(),
};

export class KlicVoiceEngine {
  isEnabled() {
    return Object.values(providers).some((provider) => provider.isEnabled());
  }

  async synthesize(text: string, preference: KlicVoicePreference): Promise<TtsSynthesisResult> {
    const voice = KLIC_VOICES[preference];
    const provider = providers[voice.provider];
    if (!provider) throw new Error('KLIC_TTS_PROVIDER_UNAVAILABLE');
    return provider.synthesize({ text, voice });
  }
}

export const klicVoiceEngine = new KlicVoiceEngine();
