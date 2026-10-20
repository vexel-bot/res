import { VoiceState } from '../types';

class VoiceAnalyzer {
  private audioCtx: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private micStream: MediaStream | null = null;
  private dataArray: Uint8Array<ArrayBuffer> | null = null;
  private isMicActive = false;

  public async toggleMicrophone(): Promise<boolean> {
    if (this.isMicActive) {
      this.stopMicrophone();
      return false;
    }

    try {
      if (typeof window === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        return false;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioCtx = new AudioContextClass();
      const source = this.audioCtx.createMediaStreamSource(stream);
      this.analyser = this.audioCtx.createAnalyser();
      this.analyser.fftSize = 64;
      source.connect(this.analyser);

      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.micStream = stream;
      this.isMicActive = true;
      return true;
    } catch {
      this.isMicActive = false;
      return false;
    }
  }

  public stopMicrophone() {
    if (this.micStream) {
      this.micStream.getTracks().forEach((track) => track.stop());
      this.micStream = null;
    }
    if (this.audioCtx) {
      this.audioCtx.close().catch(() => {});
      this.audioCtx = null;
    }
    this.analyser = null;
    this.dataArray = null;
    this.isMicActive = false;
  }

  public getIsMicActive(): boolean {
    return this.isMicActive;
  }

  // Calculate audio intensity based on real mic or realistic synthesized cadence
  public getVoiceModulation(state: VoiceState, time: number): {
    volume: number;
    ribbonWaveSpeed: number;
    waveAmplitude: number;
    pulseScale: number;
    frequencyJitter: number;
  } {
    // If real microphone is active and we are in listening mode
    if (this.isMicActive && this.analyser && this.dataArray) {
      this.analyser.getByteFrequencyData(this.dataArray);
      let sum = 0;
      for (let i = 0; i < this.dataArray.length; i++) {
        sum += this.dataArray[i];
      }
      const rawVol = sum / (this.dataArray.length * 255); // 0 to 1
      const normalizedVol = Math.min(1, rawVol * 2.5);

      if (state === 'listening') {
        return {
          volume: normalizedVol,
          ribbonWaveSpeed: 2.2 + normalizedVol * 4.0,
          waveAmplitude: 0.15 + normalizedVol * 0.45,
          pulseScale: 1 + normalizedVol * 0.12,
          frequencyJitter: normalizedVol * 1.5,
        };
      }
    }

    if (state === 'idle') {
      // Serene resting breathing
      const breath = Math.sin(time * 1.4) * 0.02;
      return {
        volume: 0,
        ribbonWaveSpeed: 1.5,
        waveAmplitude: 0.28,
        pulseScale: 1 + breath,
        frequencyJitter: 0.05,
      };
    }

    if (state === 'listening') {
      // Listening mode:
      // Attentive audio visualizer ripple: rapid concentric frequency ripples and rhythmic listening heartbeat
      const listenPulse = Math.pow(Math.sin(time * 3.8), 4) * 0.06;
      const rippleVolume = (Math.sin(time * 5.0) * 0.5 + 0.5) * 0.5;

      return {
        volume: rippleVolume,
        ribbonWaveSpeed: 3.2,
        waveAmplitude: 0.38 + listenPulse * 1.5,
        pulseScale: 1.0 + listenPulse,
        frequencyJitter: 0.25,
      };
    }

    // state === 'speaking'
    // Natural speech cadence simulation: vocalic bursts and pauses
    // Intermittent cadence (syllables -> pause -> syllables)
    const syllabic1 = Math.sin(time * 6.5);
    const syllabic2 = Math.cos(time * 2.8);
    const syllabic3 = Math.sin(time * 13.0);
    // Burst envelope with natural conversational pauses
    const cadence = Math.max(0, syllabic1 * syllabic2 + 0.35 * syllabic3);
    const speakingVol = Math.pow(cadence, 1.4);

    return {
      volume: speakingVol,
      ribbonWaveSpeed: 3.8 + speakingVol * 3.5,
      waveAmplitude: 0.30 + speakingVol * 0.45,
      pulseScale: 1.0 + speakingVol * 0.14,
      frequencyJitter: speakingVol * 0.6,
    };
  }
}

export const voiceAnalyzer = new VoiceAnalyzer();
