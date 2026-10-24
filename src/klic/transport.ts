import type { Conversation } from './conversation';

export async function readKlicJson<T = unknown>(response: Response): Promise<T> {
  let data: unknown;
  try { data = await response.json(); }
  catch {
    throw new Error(response.ok ? 'O servidor retornou uma resposta inválida.' : `Não foi possível consultar a KLIC (HTTP ${response.status}). Tente novamente.`);
  }
  const error = data && typeof data === 'object' ? Reflect.get(data, 'error') : undefined;
  if (!response.ok) throw new Error(typeof error === 'string' ? error : `Não foi possível consultar a KLIC (HTTP ${response.status}).`);
  return data as T;
}

export async function requestKlicJson<T>(url: string, init: RequestInit, timeoutMs = 30000): Promise<T> {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(new DOMException('O servidor demorou demais para responder. Tente novamente.', 'TimeoutError')), timeoutMs);
  const signal = init.signal ? AbortSignal.any([init.signal, timeout.signal]) : timeout.signal;
  try { return await readKlicJson<T>(await fetch(url, { ...init, signal })); }
  catch (error) {
    if (signal.aborted) throw signal.reason;
    if (error instanceof TypeError) throw new Error('Não foi possível conectar à Clicko. Verifique sua conexão e tente novamente.');
    throw error;
  } finally { clearTimeout(timer); }
}

type StreamEvent =
  | { type: 'accepted' | 'done'; data: Conversation }
  | { type: 'phase' | 'delta'; data: string }
  | { type: 'error'; data: { conversation: Conversation; message: string; code?: string; requestId?: string; retryable?: boolean } };
/** Reads UTF-8 incrementally, including a final unterminated line; terminal events stop the stream. */
export async function consumeKlicStream(body: ReadableStream<Uint8Array>, receive: (event: StreamEvent) => void) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffered = '';
  let finished = false;
  const consume = (line: string) => {
    if (!line.trim()) return;
    let parsed: unknown;
    try { parsed = JSON.parse(line); } catch { throw new Error('A resposta da KLIC chegou em formato inválido. Tente novamente.'); }
    if (!parsed || typeof parsed !== 'object') throw new Error('Evento de resposta da KLIC inválido.');
    const type = Reflect.get(parsed, 'type');
    const data = Reflect.get(parsed, 'data');
    if (!['accepted','phase','delta','done','error'].includes(String(type))) throw new Error('Evento de resposta da KLIC inválido.');
    if (['phase','delta'].includes(String(type)) && typeof data !== 'string') throw new Error('Conteúdo de resposta da KLIC inválido.');
    const conversation = type === 'error' && data && typeof data === 'object' ? Reflect.get(data, 'conversation') : data;
    const conversationId = conversation && typeof conversation === 'object' ? Reflect.get(conversation, 'id') : undefined;
    const messages = conversation && typeof conversation === 'object' ? Reflect.get(conversation, 'messages') : undefined;
    if (['accepted','done','error'].includes(String(type)) && (!conversationId || !Array.isArray(messages))) throw new Error('Histórico de resposta da KLIC inválido.');
    const event = parsed as StreamEvent;
    receive(event);
    finished = event.type === 'done' || event.type === 'error';
  };
  try {
    while (!finished) {
      const { value, done } = await reader.read();
      buffered += decoder.decode(value, { stream: !done });
      if (buffered.length > 64 * 1024 * 1024) throw new Error('A resposta excedeu o limite de transferência.');
      let index: number;
      while (!finished && (index = buffered.indexOf('\n')) >= 0) {
        const line = buffered.slice(0, index); buffered = buffered.slice(index + 1); consume(line);
      }
      if (done) { if (!finished && buffered.trim()) consume(buffered); break; }
    }
    if (!finished) throw new Error('A conexão foi interrompida durante a resposta. Tente novamente.');
  } finally {
    // Do not wait indefinitely for a proxy to close after the terminal event.
    void reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}
