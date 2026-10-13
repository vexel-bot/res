import { TextToSpeechClient } from '@google-cloud/text-to-speech';
import { klicTtsEnabled } from '../config';
import type { TtsProvider, TtsSynthesisRequest, TtsSynthesisResult } from '../types';

export class GoogleCloudTtsProvider implements TtsProvider {
  readonly id = 'google' as const;
  private client?: TextToSpeechClient;

  isEnabled() {
    return klicTtsEnabled();
  }

  private getClient() {
    if (!this.client) {
      this.client = new TextToSpeechClient({
        projectId: process.env.GOOGLE_CLOUD_PROJECT || undefined,
        apiEndpoint: process.env.GOOGLE_CLOUD_TTS_API_ENDPOINT || undefined,
      });
    }
    return this.client;
  }

  async synthesize({ text, voice }: TtsSynthesisRequest): Promise<TtsSynthesisResult> {
    if (!this.isEnabled()) {
      throw new Error('KLIC_TTS_DISABLED');
    }

    const [response] = await this.getClient().synthesizeSpeech({
      input: { text },
      voice: {
        languageCode: voice.languageCode,
        name: voice.voiceName,
      },
      audioConfig: { audioEncoding: 'MP3' },
    }, { timeout: 20000 });

    if (!response.audioContent) {
      throw new Error('KLIC_TTS_EMPTY_AUDIO');
    }

    const audio = typeof response.audioContent === 'string'
      ? Buffer.from(response.audioContent, 'base64')
      : Buffer.from(response.audioContent);

    return { audio, contentType: 'audio/mpeg' };
  }
}
