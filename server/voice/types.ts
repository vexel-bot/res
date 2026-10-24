export type KlicVoicePreference = 'male' | 'female';

export type KlicVoiceIdentity = {
  label: 'KLIC Male' | 'KLIC Female';
  provider: 'google';
  languageCode: 'pt-BR';
  voiceName: string;
};

export type TtsSynthesisRequest = {
  text: string;
  voice: KlicVoiceIdentity;
};

export type TtsSynthesisResult = {
  audio: Buffer;
  contentType: 'audio/mpeg';
};

export interface TtsProvider {
  readonly id: KlicVoiceIdentity['provider'];
  isEnabled(): boolean;
  synthesize(request: TtsSynthesisRequest): Promise<TtsSynthesisResult>;
}
