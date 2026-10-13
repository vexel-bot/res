import { Router } from 'express';
import { isKlicVoicePreference, KLIC_VOICES } from './config';
import { klicVoiceEngine } from './klicVoiceEngine';
import { authenticate, readKlicGovernance } from '../governance';
import { canAccessNavigation } from '../../src/security/accessControl';

const MAX_TEXT_LENGTH = 4_500;

const publicVoice = (id: 'male' | 'female') => ({
  id,
  label: KLIC_VOICES[id].label,
});

export function createKlicVoiceRouter() {
  const router = Router();
  router.use(authenticate);
  const requests = new Map<string, { until: number; count: number }>();
  router.use((req, res, next) => {
    const auth = (req as Parameters<typeof authenticate>[0]).auth!;
    const { user, accountType } = readKlicGovernance(auth);
    if (!canAccessNavigation(user, 'ai-chat', accountType)) return res.status(403).json({ error: 'Acesso à voz indisponível.' });
    if (req.headers.origin) {
      try { if (new URL(req.headers.origin).host !== req.headers.host) return res.status(403).json({ error: 'Origem inválida.' }); }
      catch { return res.status(403).json({ error: 'Origem inválida.' }); }
    }
    for (const [key, entry] of requests) if (entry.until < Date.now()) requests.delete(key);
    const key = `${auth.workspaceId}:${user.id}`;
    const entry = requests.get(key) || { until: Date.now() + 60000, count: 0 };
    if (++entry.count > 40) return res.status(429).json({ error: 'Aguarde um momento para usar a voz novamente.' });
    requests.set(key, entry); next();
  });

  router.get('/capabilities', (_req, res) => {
    res.json({
      enabled: klicVoiceEngine.isEnabled(),
      voices: [publicVoice('male'), publicVoice('female')],
    });
  });

  router.post('/synthesize', async (req, res) => {
    const text = typeof req.body?.text === 'string' ? req.body.text.trim() : '';
    const voice = req.body?.voice;

    if (!text || text.length > MAX_TEXT_LENGTH || !isKlicVoicePreference(voice)) {
      res.status(400).json({ error: 'INVALID_KLIC_VOICE_REQUEST' });
      return;
    }

    if (!klicVoiceEngine.isEnabled()) {
      res.status(503).json({ error: 'KLIC_VOICE_UNAVAILABLE' });
      return;
    }

    try {
      const result = await klicVoiceEngine.synthesize(text, voice);
      res.set({
        'Content-Type': result.contentType,
        'Content-Length': String(result.audio.byteLength),
        'Cache-Control': 'private, no-store, max-age=0',
        'X-Content-Type-Options': 'nosniff',
      });
      res.send(result.audio);
    } catch (error) {
      const code = error instanceof Error ? error.message : 'KLIC_TTS_UNKNOWN_ERROR';
      console.error('Falha na síntese de voz da KLIC:', code);
      res.status(502).json({ error: 'KLIC_VOICE_SYNTHESIS_FAILED' });
    }
  });

  return router;
}
