import React from 'react';
import { useKlicClient } from '../klic/useKlicClient';
import { shouldFinishVoiceTurn, shouldInterruptKlicSpeech, shouldRestartVoiceCapture, type KlicVoiceMode } from '../klic/voiceConversation';
import { KlicVoiceFeedbackSession, prepareKlicVoiceFeedback } from '../klic/voiceFeedback';

export type KlicVoicePhase = 'idle' | 'requesting_permission' | 'listening' | 'transcribing' | 'thinking' | 'speaking' | 'paused' | 'error' | 'ended';

type UseKlicVoiceOptions = {
  onInterim: (transcript: string) => void;
  onFinal: (transcript: string, mode: KlicVoiceMode) => void;
  processing?: boolean;
};

export type KlicVoiceProfile = 'female' | 'male';
export type { KlicVoiceMode } from '../klic/voiceConversation';

const VOICE_PROFILE_KEY = 'clicko:klic-voice-profile';
const femaleVoicePattern = /female|feminina|mulher|maria|francisca|fernanda|luciana|camila|carolina|adriana|let[ií]cia|vit[oó]ria|helo[ií]sa|lara|thais/i;
const maleVoicePattern = /male|masculina|homem|antonio|ant[oô]nio|ricardo|felipe|daniel|jo[aã]o|paulo|thiago|leandro|bruno|fabio|f[aá]bio/i;

const initialVoiceProfile = (): KlicVoiceProfile => {
  try {
    return window.localStorage.getItem(VOICE_PROFILE_KEY) === 'male' ? 'male' : 'female';
  } catch {
    return 'female';
  }
};

const speechText = (value: string) => value
  .replace(/```[\s\S]*?```/g, ' ')
  .replace(/https?:\/\/\S+/g, ' ')
  .replace(/[*_#`>|~]/g, '')
  .replace(/\s+/g, ' ')
  .trim();

const speechChunks = (value: string) => {
  const clean = speechText(value);
  if (!clean) return [];
  const sentences = clean.match(/[^.!?;:]+[.!?;:]?|[^.!?;:]+$/g) || [clean];
  const chunks: string[] = [];
  let current = '';
  sentences.forEach((sentence) => {
    const part = sentence.trim();
    if (!part) return;
    if (part.length > 240) {
      if (current) chunks.push(current);
      current = '';
      const words = part.split(/\s+/);
      let segment = '';
      words.forEach((word) => {
        if (`${segment} ${word}`.trim().length <= 220) segment = `${segment} ${word}`.trim();
        else {
          if (segment) chunks.push(segment);
          segment = word;
        }
      });
      if (segment) chunks.push(segment);
      return;
    }
    if (`${current} ${part}`.trim().length <= 240) {
      current = `${current} ${part}`.trim();
      return;
    }
    if (current) chunks.push(current);
    current = part;
  });
  if (current) chunks.push(current);
  return chunks;
};

const voiceForProfile = (profile: KlicVoiceProfile) => {
  const voices = window.speechSynthesis?.getVoices?.() || [];
  const portuguese = voices.filter((voice) => /^pt(?:-|_)/i.test(voice.lang));
  const candidates = portuguese.length ? portuguese : voices;
  const preferredPattern = profile === 'female' ? femaleVoicePattern : maleVoicePattern;
  const oppositePattern = profile === 'female' ? maleVoicePattern : femaleVoicePattern;
  return candidates.find((voice) => preferredPattern.test(voice.name))
    || candidates.find((voice) => !oppositePattern.test(voice.name))
    || candidates[profile === 'male' && candidates.length > 1 ? 1 : 0];
};

export function useKlicVoice({ onInterim, onFinal, processing = false }: UseKlicVoiceOptions) {
  const klic = useKlicClient();
  const klicRef = React.useRef(klic); klicRef.current = klic;
  const recorderRef = React.useRef<MediaRecorder | null>(null);
  const transcriptionRef = React.useRef<AbortController | null>(null);
  const captureGeneration = React.useRef(0);
  const [phase, setPhaseState] = React.useState<KlicVoicePhase>('idle');
  const [intensity, setIntensity] = React.useState(0);
  const [voiceEnabled, setVoiceEnabled] = React.useState(false);
  const [voicePaused, setVoicePaused] = React.useState(false);
  const [voiceMode, setVoiceMode] = React.useState<KlicVoiceMode | null>(null);
  const [voiceProfile, setVoiceProfileState] = React.useState<KlicVoiceProfile>(initialVoiceProfile);
  const [errorMessage, setErrorMessage] = React.useState<string>();
  const phaseRef = React.useRef<KlicVoicePhase>('idle');
  const feedbackRef = React.useRef<KlicVoiceFeedbackSession | null>(null);
  feedbackRef.current ||= new KlicVoiceFeedbackSession();
  const lastIntensityAtRef = React.useRef(0);
  const sessionActiveRef = React.useRef(false);
  const modeRef = React.useRef<KlicVoiceMode | null>(null);
  const pausedRef = React.useRef(false);
  const processingRef = React.useRef(processing);
  const streamRef = React.useRef<MediaStream | null>(null);
  const audioContextRef = React.useRef<AudioContext | null>(null);
  const animationRef = React.useRef<number | null>(null);
  const speechPulseRef = React.useRef<number | null>(null);
  const restartTimerRef = React.useRef<number | null>(null);
  const serverAudioRef = React.useRef<HTMLAudioElement | null>(null);
  const serverAudioUrlRef = React.useRef<string | undefined>(undefined);
  const synthesisAbortRef = React.useRef<AbortController | null>(null);
  const playbackGenerationRef = React.useRef(0);
  const settlePlaybackRef = React.useRef<(() => void) | null>(null);
  const startInProgressRef = React.useRef(false);
  const captureRecoveryRef = React.useRef(0);
  const restartListeningRef = React.useRef<() => void>(() => {});
  const bargeStreamRef = React.useRef<MediaStream | null>(null);
  const bargeContextRef = React.useRef<AudioContext | null>(null);
  const bargeAnimationRef = React.useRef<number | null>(null);
  const bargeInProgressRef = React.useRef(false);
  const interruptSpeechRef = React.useRef<() => void>(() => {});
  const onInterimRef = React.useRef(onInterim);
  const onFinalRef = React.useRef(onFinal);

  React.useEffect(() => { onInterimRef.current = onInterim; }, [onInterim]);
  React.useEffect(() => { onFinalRef.current = onFinal; }, [onFinal]);
  React.useEffect(() => { processingRef.current = processing; }, [processing]);

  const voiceSupported = typeof window !== 'undefined'
    && typeof MediaRecorder !== 'undefined'
    && typeof navigator !== 'undefined'
    && Boolean(navigator.mediaDevices?.getUserMedia);

  const setPhase = React.useCallback((next: KlicVoicePhase) => {
    phaseRef.current = next;
    setPhaseState(next);
  }, []);

  const clearRestartTimer = React.useCallback(() => {
    if (restartTimerRef.current !== null) window.clearTimeout(restartTimerRef.current);
    restartTimerRef.current = null;
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

  const stopBargeInMonitor = React.useCallback(() => {
    if (bargeAnimationRef.current !== null) cancelAnimationFrame(bargeAnimationRef.current);
    bargeAnimationRef.current = null;
    bargeStreamRef.current?.getTracks().forEach((track) => track.stop());
    bargeStreamRef.current = null;
    if (bargeContextRef.current && bargeContextRef.current.state !== 'closed') void bargeContextRef.current.close();
    bargeContextRef.current = null;
    bargeInProgressRef.current = false;
  }, []);

  const startBargeInMonitor = React.useCallback(async () => {
    if (pausedRef.current || modeRef.current !== 'conversation' || bargeInProgressRef.current || bargeStreamRef.current) return;
    bargeInProgressRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      if (pausedRef.current || modeRef.current !== 'conversation' || phaseRef.current !== 'speaking') {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      bargeStreamRef.current = stream;
      const context = new AudioContext();
      bargeContextRef.current = context;
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);
      let voiceStartedAt = 0;
      const measure = () => {
        if (phaseRef.current !== 'speaking' || pausedRef.current || modeRef.current !== 'conversation') { stopBargeInMonitor(); return; }
        analyser.getByteTimeDomainData(samples);
        let power = 0;
        for (const sample of samples) power += ((sample - 128) / 128) ** 2;
        const rms = Math.sqrt(power / samples.length);
        const now = performance.now();
        if (rms > 0.055) voiceStartedAt ||= now;
        else voiceStartedAt = 0;
        if (voiceStartedAt && shouldInterruptKlicSpeech(rms, now - voiceStartedAt)) { interruptSpeechRef.current(); return; }
        bargeAnimationRef.current = requestAnimationFrame(measure);
      };
      measure();
    } catch {
      // Barge-in is progressive enhancement; the primary capture remains available.
      stopBargeInMonitor();
    } finally {
      bargeInProgressRef.current = false;
    }
  }, [stopBargeInMonitor]);

  const stopSpeechPulse = React.useCallback(() => {
    if (speechPulseRef.current !== null) window.clearInterval(speechPulseRef.current);
    speechPulseRef.current = null;
    setIntensity(0);
  }, []);

  const startSpeechPulse = React.useCallback(() => {
    if (speechPulseRef.current !== null) return;
    let tick = 0;
    speechPulseRef.current = window.setInterval(() => {
      tick += 1;
      const wave = (Math.sin(tick * 0.93) + Math.sin(tick * 0.37 + 1.2) + 2) / 4;
      setIntensity(0.22 + wave * 0.63);
    }, 76);
  }, []);

  const clearServerPlayback = React.useCallback(() => {
    stopBargeInMonitor();
    settlePlaybackRef.current?.();
    settlePlaybackRef.current = null;
    synthesisAbortRef.current?.abort();
    synthesisAbortRef.current = null;
    const audio = serverAudioRef.current;
    serverAudioRef.current = null;
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
    }
    if (serverAudioUrlRef.current) URL.revokeObjectURL(serverAudioUrlRef.current);
    serverAudioUrlRef.current = undefined;
  }, [stopBargeInMonitor]);

  const clearRecognition = React.useCallback(() => {
    captureGeneration.current++;
    transcriptionRef.current?.abort(); transcriptionRef.current=null;
    const recorder=recorderRef.current; recorderRef.current=null;
    if(recorder){recorder.ondataavailable=null;recorder.onstop=null;recorder.onerror=null;if(recorder.state!=='inactive')recorder.stop();}
    stopAudioAnalysis();
  },[stopAudioAnalysis]);

  const showError = React.useCallback((message: string) => {
    feedbackRef.current?.listeningEnded();
    sessionActiveRef.current = false;
    pausedRef.current = false;
    setVoiceEnabled(false);
    setVoicePaused(false);
    setVoiceMode(null);
    modeRef.current = null;
    setErrorMessage(message);
    clearRestartTimer();
    clearRecognition();
    stopSpeechPulse();
    clearServerPlayback();
    window.speechSynthesis?.cancel();
    setPhase('error');
  }, [clearRecognition, clearRestartTimer, clearServerPlayback, setPhase, stopSpeechPulse]);

  const startListening = React.useCallback(async () => {
    if (!sessionActiveRef.current || pausedRef.current || startInProgressRef.current || recorderRef.current || transcriptionRef.current || phaseRef.current==='speaking' || serverAudioRef.current || synthesisAbortRef.current) return;
    if(processingRef.current){setPhase('thinking');return;}
    if(!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder==='undefined'){showError('A conversa por voz não é compatível com este navegador.');return;}
    startInProgressRef.current=true;clearRestartTimer();setErrorMessage(undefined);setPhase('requesting_permission');
    const generation=++captureGeneration.current;
    try{
      const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      if(!sessionActiveRef.current || pausedRef.current || generation!==captureGeneration.current){stream.getTracks().forEach(track=>track.stop());return;}
      streamRef.current=stream;
      const mime=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus'].find(type=>MediaRecorder.isTypeSupported(type));
      if(!mime)throw new Error('unsupported');
      const recorder=new MediaRecorder(stream,{mimeType:mime,audioBitsPerSecond:64000});recorderRef.current=recorder;
      const chunks:BlobPart[]=[];let size=0;
      recorder.ondataavailable=event=>{if(event.data.size){size+=event.data.size;chunks.push(event.data);if(size>5*1024*1024 && recorder.state==='recording')recorder.stop();}};
      recorder.onerror=()=>{
        recorder.onstop=null;
        recorderRef.current=null;
        captureGeneration.current++;
        stopAudioAnalysis();
        if(modeRef.current==='conversation'&&sessionActiveRef.current&&!pausedRef.current&&captureRecoveryRef.current<2){
          captureRecoveryRef.current+=1;
          setPhase('requesting_permission');
          clearRestartTimer();
          restartTimerRef.current=window.setTimeout(()=>restartListeningRef.current(),500);
          return;
        }
        showError('A gravação foi interrompida. Tente novamente.');
      };
      recorder.onstop=()=>{
        recorderRef.current=null;stopAudioAnalysis();
        if(generation!==captureGeneration.current || !sessionActiveRef.current || pausedRef.current)return;
        if(modeRef.current==='dictation')feedbackRef.current?.listeningEnded();
        setPhase('transcribing');
        void(async()=>{
          const controller=new AbortController();transcriptionRef.current=controller;
          let timedOut=false;
          const timeout=window.setTimeout(()=>{timedOut=true;controller.abort();},55000);
          try{
            const type=mime.split(';')[0];const blob=new Blob(chunks,{type});
            const dataUrl=await new Promise<string>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(reader.error);reader.readAsDataURL(blob);});
            const result=await klicRef.current.request<{transcript:string}>('conversations/transcribe','ai-chat',{attachment:{name:type==='audio/ogg'?'voz.ogg':'voz.webm',type,size:blob.size,dataUrl}},controller.signal);
            if(generation!==captureGeneration.current || !sessionActiveRef.current || pausedRef.current)return;
            const mode = modeRef.current || 'conversation';
            captureRecoveryRef.current=0;
            onInterimRef.current(result.transcript);
            onFinalRef.current(result.transcript, mode);
            if (mode === 'dictation') {
              sessionActiveRef.current = false;
              modeRef.current = null;
              setVoiceEnabled(false);
              setVoiceMode(null);
              setPhase('idle');
            }
          }catch(error){if(timedOut && generation===captureGeneration.current && sessionActiveRef.current)showError('A transcrição demorou demais. Tente novamente.');else if(!controller.signal.aborted)showError(error instanceof Error && error.message.includes('acesso')?error.message:'Não foi possível transcrever a fala. Tente novamente ou use texto.');}
          finally{window.clearTimeout(timeout);if(transcriptionRef.current===controller)transcriptionRef.current=null;}
        })();
      };
      const context=new AudioContext();audioContextRef.current=context;
      const analyser=context.createAnalyser();analyser.fftSize=1024;context.createMediaStreamSource(stream).connect(analyser);
      const samples=new Uint8Array(analyser.fftSize);const started=performance.now();let lastVoice=started;let heardVoice=false;
      const measure=()=>{
        if(generation!==captureGeneration.current || recorder.state!=='recording')return;
        analyser.getByteTimeDomainData(samples);let power=0;for(const sample of samples)power+=((sample-128)/128)**2;const rms=Math.sqrt(power/samples.length);
        const now=performance.now();
        if(now-lastIntensityAtRef.current>=50){lastIntensityAtRef.current=now;setIntensity(Math.min(1,rms*12));}
        if(rms>.025){heardVoice=true;lastVoice=now;}
        const boundary=shouldFinishVoiceTurn({elapsedMs:now-started,silenceMs:now-lastVoice,heardVoice});
        if(boundary==='no-speech'){
          if(modeRef.current==='conversation'){
            clearRecognition();
            setPhase('requesting_permission');
            clearRestartTimer();
            restartTimerRef.current=window.setTimeout(()=>restartListeningRef.current(),300);
          } else showError('Nenhuma fala foi detectada. Tente novamente.');
          return;
        }
        if(boundary==='complete'){recorder.stop();return;}
        animationRef.current=requestAnimationFrame(measure);
      };
      recorder.start(250);setPhase('listening');feedbackRef.current?.listeningStarted();measure();
    }catch(error){
      const denied=error instanceof DOMException&&['NotAllowedError','SecurityError'].includes(error.name);
      showError(denied?'Permita o acesso ao microfone para conversar com a KLIC.':'Não foi possível iniciar o microfone.');
    }finally{startInProgressRef.current=false;}
  },[clearRestartTimer,setPhase,showError,stopAudioAnalysis]);
  restartListeningRef.current=()=>{void startListening();};

  const interruptSpeech = React.useCallback(() => {
    if (!sessionActiveRef.current || modeRef.current !== 'conversation' || phaseRef.current !== 'speaking') return;
    playbackGenerationRef.current += 1;
    clearServerPlayback();
    window.speechSynthesis?.cancel();
    stopSpeechPulse();
    setPhase('idle');
    restartTimerRef.current = window.setTimeout(() => { void startListening(); }, 80);
  }, [clearServerPlayback, setPhase, startListening, stopSpeechPulse]);
  interruptSpeechRef.current = interruptSpeech;

  const finishSpeech = React.useCallback((generation: number) => {
    if (generation !== playbackGenerationRef.current || !sessionActiveRef.current) return;
    clearServerPlayback();
    stopSpeechPulse();
    setPhase(pausedRef.current ? 'paused' : 'idle');
    if (shouldRestartVoiceCapture(modeRef.current, pausedRef.current)) restartTimerRef.current = window.setTimeout(() => { void startListening(); }, 320);
  }, [clearServerPlayback, setPhase, startListening, stopSpeechPulse]);

  const speakWithBrowser = React.useCallback((text: string, generation: number) => {
    if (!window.speechSynthesis || !('SpeechSynthesisUtterance' in window)) {
      showError('A reprodução de voz não está disponível neste navegador.');
      return;
    }
    const chunks = speechChunks(text);
    let chunkIndex = 0;
    const speakNext = () => {
      if (!sessionActiveRef.current || generation !== playbackGenerationRef.current) return;
      const chunk = chunks[chunkIndex];
      if (!chunk) {
        finishSpeech(generation);
        return;
      }
      const utterance = new SpeechSynthesisUtterance(chunk);
      utterance.lang = 'pt-BR';
      utterance.rate = voiceProfile === 'female' ? 1.01 : 0.98;
      utterance.pitch = voiceProfile === 'female' ? 1.06 : 0.88;
      const selectedVoice = voiceForProfile(voiceProfile);
      if (selectedVoice) utterance.voice = selectedVoice;
      utterance.onstart = () => {
        setPhase('speaking');
        startSpeechPulse();
        void startBargeInMonitor();
      };
      utterance.onend = () => {
        chunkIndex += 1;
        speakNext();
      };
      utterance.onerror = (event) => {
        if (event.error === 'canceled' || event.error === 'interrupted') return;
        showError('A resposta por voz foi interrompida.');
      };
      window.speechSynthesis.speak(utterance);
    };
    speakNext();
  }, [finishSpeech, setPhase, showError, startBargeInMonitor, startSpeechPulse, voiceProfile]);

  const speak = React.useCallback((text: string) => {
    if (!sessionActiveRef.current || !text.trim()) return;
    if (pausedRef.current) {
      return;
    }

    const chunks = speechChunks(text);
    if (!chunks.length) {
      void startListening();
      return;
    }

    const generation = playbackGenerationRef.current + 1;
    playbackGenerationRef.current = generation;
    clearRecognition();
    clearServerPlayback();
    window.speechSynthesis?.cancel();
    stopSpeechPulse();

    void (async () => {
      let chunkIndex = 0;
      try {
        for (; chunkIndex < chunks.length; chunkIndex += 1) {
          if (!sessionActiveRef.current || generation !== playbackGenerationRef.current) return;

          const abortController = new AbortController();
          synthesisAbortRef.current = abortController;
          const response = await fetch('/api/klic/voice/synthesize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: chunks[chunkIndex], voice: voiceProfile }),
            signal: abortController.signal,
          });
          synthesisAbortRef.current = null;
          if (!response.ok) throw new Error(`KLIC_TTS_HTTP_${response.status}`);

          const audioBlob = await response.blob();
          if (!audioBlob.size) throw new Error('KLIC_TTS_EMPTY_AUDIO');
          if (!sessionActiveRef.current || generation !== playbackGenerationRef.current) return;

          const audioUrl = URL.createObjectURL(audioBlob);
          serverAudioUrlRef.current = audioUrl;
          const audio = new Audio(audioUrl);
          serverAudioRef.current = audio;
          setPhase('speaking');
          startSpeechPulse();
          void startBargeInMonitor();
          await new Promise<void>((resolve, reject) => {
            settlePlaybackRef.current = () => reject(new DOMException('Reprodução interrompida.', 'AbortError'));
            audio.onended = () => resolve();
            audio.onerror = () => reject(new Error('KLIC_TTS_PLAYBACK_FAILED'));
            void audio.play().catch(reject);
          });
          settlePlaybackRef.current = null;
          serverAudioRef.current = null;
          URL.revokeObjectURL(audioUrl);
          serverAudioUrlRef.current = undefined;
        }
        finishSpeech(generation);
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        if (!sessionActiveRef.current || generation !== playbackGenerationRef.current) return;
        clearServerPlayback();
        stopSpeechPulse();
        speakWithBrowser(chunks.slice(chunkIndex).join(' '), generation);
      }
    })();
  }, [clearRecognition, clearServerPlayback, finishSpeech, speakWithBrowser, startBargeInMonitor, startListening, startSpeechPulse, stopSpeechPulse, voiceProfile]);

  const beginVoice = React.useCallback((mode: KlicVoiceMode) => {
    if (!voiceSupported) {
      showError('A conversa por voz não é compatível com este navegador.');
      return;
    }
    prepareKlicVoiceFeedback();
    sessionActiveRef.current = true;
    modeRef.current = mode;
    captureRecoveryRef.current = 0;
    pausedRef.current = false;
    setVoiceEnabled(true);
    setVoicePaused(false);
    setVoiceMode(mode);
    setErrorMessage(undefined);
    void startListening();
  }, [showError, startListening, voiceSupported]);

  const startConversation = React.useCallback(() => beginVoice('conversation'), [beginVoice]);
  const startDictation = React.useCallback(() => beginVoice('dictation'), [beginVoice]);

  const endConversation = React.useCallback(() => {
    feedbackRef.current?.listeningEnded();
    sessionActiveRef.current = false;
    modeRef.current = null;
    pausedRef.current = false;
    setVoiceEnabled(false);
    setVoicePaused(false);
    setVoiceMode(null);
    setErrorMessage(undefined);
    clearRestartTimer();
    clearRecognition();
    stopSpeechPulse();
    playbackGenerationRef.current += 1;
    clearServerPlayback();
    window.speechSynthesis?.cancel();
    setPhase('ended');
  }, [clearRecognition, clearRestartTimer, clearServerPlayback, setPhase, stopSpeechPulse]);

  React.useEffect(() => { endConversation(); }, [klic.scope, endConversation]);

  const pauseConversation = React.useCallback(() => {
    if (!sessionActiveRef.current || pausedRef.current) return;
    feedbackRef.current?.listeningEnded();
    pausedRef.current = true;
    setVoicePaused(true);
    clearRestartTimer();
    clearRecognition();
    stopBargeInMonitor();
    if (phaseRef.current !== 'speaking') setPhase('paused');
  }, [clearRecognition, clearRestartTimer, setPhase, stopBargeInMonitor]);

  const resumeConversation = React.useCallback(() => {
    if (!sessionActiveRef.current || !pausedRef.current) return;
    prepareKlicVoiceFeedback();
    pausedRef.current = false;
    setVoicePaused(false);
    if (phaseRef.current !== 'speaking') void startListening();
  }, [startListening]);

  const finishDictation = React.useCallback(() => {
    const recorder = recorderRef.current;
    if (modeRef.current === 'dictation' && recorder?.state === 'recording') {
      feedbackRef.current?.listeningEnded();
      recorder.stop();
    }
  }, []);

  const setVoiceProfile = React.useCallback((profile: KlicVoiceProfile) => {
    setVoiceProfileState(profile);
    try { window.localStorage.setItem(VOICE_PROFILE_KEY, profile); } catch { /* Preference remains valid for this session. */ }
  }, []);

  const previewVoice = React.useCallback(async (profile: KlicVoiceProfile) => {
    clearRecognition();
    clearRestartTimer();
    const previewText = 'Como posso ajudar?';
    const generation = playbackGenerationRef.current + 1;
    playbackGenerationRef.current = generation;
    clearServerPlayback();
    window.speechSynthesis?.cancel();
    stopSpeechPulse();
    setErrorMessage(undefined);

    const playBrowserPreview = () => {
      if (!window.speechSynthesis || !('SpeechSynthesisUtterance' in window)) {
        setErrorMessage('A prévia de voz não está disponível neste navegador.');
        setPhase('idle');
        return;
      }
      const utterance = new SpeechSynthesisUtterance(previewText);
      utterance.lang = 'pt-BR';
      utterance.rate = profile === 'female' ? 1.01 : 0.98;
      utterance.pitch = profile === 'female' ? 1.06 : 0.88;
      const selectedVoice = voiceForProfile(profile);
      if (selectedVoice) utterance.voice = selectedVoice;
      utterance.onstart = () => {
        if (generation !== playbackGenerationRef.current) return;
        setPhase('speaking');
        startSpeechPulse();
      };
      utterance.onend = () => {
        if (generation !== playbackGenerationRef.current) return;
        stopSpeechPulse();
        setPhase('idle');
      };
      utterance.onerror = (event) => {
        if (event.error === 'canceled' || event.error === 'interrupted') return;
        stopSpeechPulse();
        setPhase('idle');
        setErrorMessage('Não foi possível reproduzir a prévia de voz.');
      };
      window.speechSynthesis.speak(utterance);
    };

    try {
      const abortController = new AbortController();
      synthesisAbortRef.current = abortController;
      const response = await fetch('/api/klic/voice/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: previewText, voice: profile }),
        signal: abortController.signal,
      });
      synthesisAbortRef.current = null;
      if (!response.ok) throw new Error(`KLIC_TTS_HTTP_${response.status}`);
      const audioBlob = await response.blob();
      if (!audioBlob.size || generation !== playbackGenerationRef.current) return;

      const audioUrl = URL.createObjectURL(audioBlob);
      serverAudioUrlRef.current = audioUrl;
      const audio = new Audio(audioUrl);
      serverAudioRef.current = audio;
      audio.onended = () => {
        if (generation !== playbackGenerationRef.current) return;
        clearServerPlayback();
        stopSpeechPulse();
        setPhase('idle');
      };
      audio.onerror = () => {
        if (generation !== playbackGenerationRef.current) return;
        clearServerPlayback();
        stopSpeechPulse();
        playBrowserPreview();
      };
      setPhase('speaking');
      startSpeechPulse();
      await audio.play();
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      if (generation !== playbackGenerationRef.current) return;
      clearServerPlayback();
      stopSpeechPulse();
      playBrowserPreview();
    }
  }, [clearRecognition, clearRestartTimer, clearServerPlayback, setPhase, startSpeechPulse, stopSpeechPulse]);

  React.useEffect(() => () => {
    feedbackRef.current?.listeningEnded();
    sessionActiveRef.current = false;
    clearRecognition();
    if (speechPulseRef.current !== null) window.clearInterval(speechPulseRef.current);
    if (restartTimerRef.current !== null) window.clearTimeout(restartTimerRef.current);
    playbackGenerationRef.current += 1;
    clearServerPlayback();
    window.speechSynthesis?.cancel();
  }, [clearRecognition, clearServerPlayback]);

  return {
    phase,
    intensity,
    voiceEnabled,
    voicePaused,
    voiceMode,
    voiceProfile,
    voiceSupported,
    errorMessage,
    failSession: showError,
    startConversation,
    startDictation,
    finishDictation,
    pauseConversation,
    resumeConversation,
    endConversation,
    setVoiceProfile,
    previewVoice,
    speak,
  };
}
