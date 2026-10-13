import React from 'react';
import { createPortal } from 'react-dom';
import { Mic, MicOff, X, MessageSquareText } from 'lucide-react';
import { KlicPlasma, type KlicPlasmaState } from '../components/KlicPlasma';
import { ClickoLoader } from '../components/ClickoLoader';
import type { ChatMessage } from './conversation';
import './KlicVoiceSession.css';

type Props = {
  phase: KlicPlasmaState;
  status?: string;
  intensity: number;
  muted: boolean;
  error?: string;
  profile: 'female' | 'male';
  messages: ChatMessage[];
  onMute: () => void;
  onEnd: () => void;
  onRetry: () => void;
};

const phaseLabel: Record<KlicPlasmaState, string> = {
  idle: 'Pronta para conversar',
  connecting: 'Preparando o microfone',
  listening: 'Estou ouvindo',
  processing: 'Preparando resposta',
  speaking: 'KLIC está falando',
  error: 'Conexão interrompida',
};

export function KlicVoiceSession({ phase, status, intensity, muted, error, profile, messages, onMute, onEnd, onRetry }: Props) {
  const [transcriptOpen, setTranscriptOpen] = React.useState(false);
  const endRef = React.useRef<HTMLButtonElement>(null);
  React.useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    endRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onEnd();
      if (event.key !== 'Tab') return;
      const dialog = endRef.current?.closest('[role="dialog"]');
      const controls = Array.from(dialog?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || []);
      const first = controls[0];
      const last = controls.at(-1);
      if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => { document.removeEventListener('keydown', onKeyDown); previous?.focus(); };
  }, [onEnd]);

  const recentMessages = messages.filter((message) => !message.id.startsWith('welcome-')).slice(-6);
  const statusText = error || (muted ? 'Microfone silenciado' : status || phaseLabel[phase]);

  return createPortal(
    <div className="klic-voice-session" role="dialog" aria-modal="true" aria-label="Conversa por voz com a KLIC">
      <div className="klic-voice-session__top">
        <div><strong>KLIC AI</strong><span>Conversa por voz · {profile === 'female' ? 'voz feminina' : 'voz masculina'}</span></div>
        <button ref={endRef} type="button" onClick={onEnd} aria-label="Encerrar conversa por voz" className="klic-voice-session__close"><X size={18} /></button>
      </div>
      <div className="klic-voice-session__center">
        <KlicPlasma state={muted ? 'idle' : phase} intensity={intensity} showIdentity={false} />
        <div className="klic-voice-session__status" aria-live="polite">
          {phase === 'connecting' || phase === 'processing' ? <ClickoLoader size="tiny" tone="dark" label={statusText} /> : <span className={`klic-voice-session__dot klic-voice-session__dot--${phase}`} />}
          {statusText}
        </div>
        {phase === 'error' && <button type="button" className="klic-voice-session__retry" onClick={onRetry}>Tentar novamente</button>}
        {transcriptOpen && (
          <div className="klic-voice-session__transcript" aria-label="Transcrição da conversa">
            {recentMessages.length ? recentMessages.map((message) => (
              <p key={message.id}><span>{message.role === 'user' ? 'Você' : 'KLIC'}</span>{message.content || (message.status === 'streaming' ? 'Respondendo…' : '')}</p>
            )) : <p className="klic-voice-session__empty">A transcrição aparecerá aqui durante a conversa.</p>}
          </div>
        )}
      </div>
      <div className="klic-voice-session__bottom">
        <button type="button" className="klic-voice-session__control" onClick={onMute} disabled={phase === 'error'} aria-label={muted ? 'Reativar microfone' : 'Silenciar microfone'} aria-pressed={muted}>{muted ? <MicOff size={19} /> : <Mic size={19} />}<span>{muted ? 'Reativar' : 'Silenciar'}</span></button>
        <button type="button" className="klic-voice-session__end" onClick={onEnd}>Encerrar</button>
        <button type="button" className="klic-voice-session__control" onClick={() => setTranscriptOpen((value) => !value)} aria-label={transcriptOpen ? 'Ocultar transcrição' : 'Ver transcrição'} aria-pressed={transcriptOpen}><MessageSquareText size={19} /><span>Transcrição</span></button>
      </div>
    </div>,
    document.body,
  );
}
