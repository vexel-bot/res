import { createHash } from 'node:crypto';
import { reserveStudioImageUsage, settleStudioImageUsage, type AuthContext } from '../governance';

const locks = new Map<string, Promise<void>>();
const digest = (value: string) => createHash('sha256').update(value).digest('hex');
// JSON object ordering is not part of the request's identity. Array ordering is.
function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object')
    return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}
const invalid = (message: string) => Object.assign(new Error(message), { status: 422, code: 'IMAGE_REQUEST_INVALID' });

/** One unit per admitted image job. Transport replay and the job's own retries are not new jobs. */
export async function forwardMeteredImageRequest(input: {
  auth: AuthContext;
  clientId: string | null;
  documentId: string;
  key?: string;
  body: unknown;
  signal?: AbortSignal;
  forward: (receiptId?: string) => Promise<Response>;
}) {
  const { auth, clientId, documentId, key, body } = input;
  if (!key || key.length < 8 || key.length > 160) throw invalid('Envie a identidade original do pedido para evitar consumo duplicado.');
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw invalid('Envie uma solicitação de imagem válida.');
  const request = body as Record<string, unknown>;
  if (!['generate_image', 'edit_image'].includes(String(request.operation))) throw invalid('Esta operação não pertence à geração ou edição de imagens.');
  // Backend keys are unique within its workspace (Clicko account + client), not per actor/document.
  const id = digest(JSON.stringify([auth.workspaceId, clientId, key]));
  const fingerprint = digest(canonical({ documentId, request }));
  const previous = locks.get(id) || Promise.resolve();
  let release!: () => void;
  const current = new Promise<void>(resolve => { release = resolve; });
  const tail = previous.then(() => current);
  locks.set(id, tail);
  await previous;
  try {
    input.signal?.throwIfAborted();
    reserveStudioImageUsage(auth, id, fingerprint);
    // Never release on a network error/5xx: a committed backend job may exist.
    const response = await input.forward(id);
    if (response.ok) {
      const job = await response.clone().json() as Record<string, any>;
      if (typeof job.id !== 'string' || !job.id || job.documentId !== documentId || job.idempotencyKey !== key || !['editing_gemini', 'editing_ai'].includes(job.jobType) || job.request?.input?.operation !== request.operation)
        throw Object.assign(new Error('O servidor não confirmou o registro da imagem. Verifique o mesmo pedido antes de iniciar outro.'), { status: 502, code: 'IMAGE_ADMISSION_UNCONFIRMED' });
      settleStudioImageUsage(auth, id, job.id);
    } else if ([400, 401, 403, 404, 405, 409, 413, 415, 422, 429].includes(response.status)) {
      // A rejected admission is not an accepted request, unlike an accepted job with status failed/cancelled.
      settleStudioImageUsage(auth, id);
    }
    return response;
  } finally {
    release();
    if (locks.get(id) === tail) locks.delete(id);
  }
}
