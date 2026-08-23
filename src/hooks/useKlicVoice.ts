import React from 'react';
import type { KlicPlasmaState } from '../components/KlicPlasma';

type SpeechRecognitionResultEventLike = {
  resultIndex: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

type UseKlicVoiceOptions = {
  onInterim: (transcript: string) => void;
  onFinal: (transcript: string) => void;
};

export function useKlicVoice({ onInterim, onFinal }: UseKlicVoiceOptions) {
  const [phase, setPhaseState] = React.useState<KlicPlasmaState>('idle');
  const [intensity, setIntensity] = React.useState(0);
  const [voiceEnabled, setVoiceEnabled] = React.useState(false);
  const phaseRef = React.useRef<KlicPlasmaState>('idle');
  const recognitionRef = React.useRef<any>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const animationRef = React.useRef<number | null>(null);
  const speechPulseRef = React.useRef<number | null>(null);
  const errorTimerRef = React.useRef<number | null>(null);

  const setPhase = React.useCallback((next: KlicPlasmaState) => {
    phaseRef.current = next;
    setPhaseState(next);
  }, []);

  const stopAudioAnalysis = React.useCallback(() => {
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    animationRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') void audioContextRef.current.close();
    audioContextRef.current = null;
    setIntensity(0);
  }, []);

  const stopSpeechPulse = React.useCallback(() => {
    if (speechPulseRef.current !== null) window.clearInterval(speechPulseRef.current);
    speechPulseRef.current = null;
    setIntensity(0);
  }, []);

  const stopAll = React.useCallback(() => {
    recognitionRef.current?.abort?.();
    recognitionRef.current = null;
    stopAudioAnalysis();
    stopSpeechPulse();
    window.speechSynthesis?.cancel();
    setVoiceEnabled(false);
    setPhase('idle');
  }, [setPhase, stopAudioAnalysis, stopSpeechPulse]);

  const showError = React.useCallback(() => {
    stopAudioAnalysis();
    setVoiceEnabled(false);
    setPhase('error');
    if (errorTimerRef.current !== null) window.clearTimeout(errorTimerRef.current);
    errorTimerRef.current = window.setTimeout(() => setPhase('idle'), 2200);
  }, [setPhase, stopAudioAnalysis]);

  const startListening = React.useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showError();
      return;
    }

    setVoiceEnabled(true);
    setPhase('connecting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      streamRef.current = stream;
      const AudioContextConstructor = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (AudioContextConstructor) {
        const audioContext = new AudioContextConstructor();
        audioContextRef.current = audioContext;
        const analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.76;
        audioContext.createMediaStreamSource(stream).connect(analyser);
        const samples = new Uint8Array(analyser.frequencyBinCount);
        const measure = () => {
          analyser.getByteFrequencyData(samples);
          const average = samples.reduce((sum, value) => sum + value, 0) / samples.length;
          setIntensity((current) => current * 0.58 + Math.min(1, average / 74) * 0.42);
          animationRef.current = requestAnimationFrame(measure);
        };
        measure();
      }

      const speechWindow = window as typeof window & { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any };
      const Recognition = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
      if (!Recognition) {
        showError();
        return;
      }

      const recognition = new Recognition();
      recognitionRef.current = recognition;
      recognition.lang = 'pt-BR';
      recognition.interimResults = true;
      recognition.continuous = false;
      recognition.maxAlternatives = 1;
      recognition.onstart = () => setPhase('listening');
      recognition.onresult = (event: SpeechRecognitionResultEventLike) => {
        let transcript = '';
        let finalTranscript = '';
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const part = event.results[index][0]?.transcript || '';
          transcript += part;
          if (event.results[index].isFinal) finalTranscript += part;
        }
        if (transcript.trim()) onInterim(transcript.trim());
        if (finalTranscript.trim()) {
          stopAudioAnalysis();
          setPhase('processing');
          onFinal(finalTranscript.trim());
        }
      };
      recognition.onerror = () => showError();
      recognition.onend = () => {
        recognitionRef.current = null;
        stopAudioAnalysis();
        if (phaseRef.current === 'listening' || phaseRef.current === 'connecting') setPhase('idle');
      };
      recognition.start();
    } catch {
      showError();
    }
  }, [onFinal, onInterim, setPhase, showError, stopAudioAnalysis]);

  const toggleVoice = React.useCallback(() => {
    if (voiceEnabled || phaseRef.current === 'listening' || phaseRef.current === 'speaking') {
      stopAll();
      return;
    }
    void startListening();
  }, [startListening, stopAll, voiceEnabled]);

  const speak = React.useCallback((text: string) => {
    if (!voiceEnabled || !window.speechSynthesis || !text.trim()) return;
    window.speechSynthesis.cancel();
    stopSpeechPulse();
    const utterance = new SpeechSynthesisUtterance(text.replace(/[*_#`>]/g, '').slice(0, 4200));
    utterance.lang = 'pt-BR';
    utterance.rate = 1.02;
    utterance.pitch = 1;
    const voices = window.speechSynthesis.getVoices();
    const portugueseVoice = voices.find((voice) => voice.lang.toLowerCase().startsWith('pt-br')) || voices.find((voice) => voice.lang.toLowerCase().startsWith('pt'));
    if (portugueseVoice) utterance.voice = portugueseVoice;
    utterance.onstart = () => {
      setPhase('speaking');
      let tick = 0;
      speechPulseRef.current = window.setInterval(() => {
        tick += 1;
        const wave = (Math.sin(tick * 0.93) + Math.sin(tick * 0.37 + 1.2) + 2) / 4;
        setIntensity(0.22 + wave * 0.63);
      }, 76);
    };
    utterance.onend = () => {
      stopSpeechPulse();
      setPhase('idle');
    };
    utterance.onerror = () => showError();
    window.speechSynthesis.speak(utterance);
  }, [setPhase, showError, stopSpeechPulse, voiceEnabled]);

  React.useEffect(() => () => {
    recognitionRef.current?.abort?.();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    if (animationRef.current !== null) cancelAnimationFrame(animationRef.current);
    if (speechPulseRef.current !== null) window.clearInterval(speechPulseRef.current);
    if (errorTimerRef.current !== null) window.clearTimeout(errorTimerRef.current);
    window.speechSynthesis?.cancel();
  }, []);

  return { phase, intensity, voiceEnabled, toggleVoice, speak, stopAll };
}
