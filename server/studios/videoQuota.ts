import { createHash } from 'node:crypto';
import { reserveStudioVideoUsage, settleStudioVideoUsage, reconcileStudioVideoJob, type AuthContext } from '../governance';

const digest = (value: unknown) => createHash('sha256').update(JSON.stringify(value, (_key, item) =>
  item && typeof item === 'object' && !Array.isArray(item) ? Object.fromEntries(Object.entries(item).sort(([a], [b]) => a.localeCompare(b))) : item)).digest('hex');

export async function forwardMeteredVideoRequest(input: { auth: AuthContext; clientId: string | null; documentId: string; key?: string; body: any; forward: (receiptId?: string) => Promise<Response> }) {
  if (input.body?.operation !== 'generate_video') return input.forward();
  if (!input.key || input.key.length < 8 || input.key.length > 160)
    throw Object.assign(new Error('Use a identidade original do pedido de vídeo.'), { status: 422, code: 'VIDEO_REQUEST_INVALID' });
  const id = digest([input.auth.workspaceId, input.clientId, input.key]);
  reserveStudioVideoUsage(input.auth, id, digest({ documentId: input.documentId, body: input.body }), Number(input.body.durationSeconds ?? 8));
  const response = await input.forward(id);
  if (response.ok) {
    const job = await response.clone().json();
    if (!job.id || job.documentId !== input.documentId || job.idempotencyKey !== input.key || job.request?.input?.operation !== 'generate_video')
      throw Object.assign(new Error('O servidor não confirmou o vídeo. Confira o mesmo pedido.'), { status: 502, code: 'VIDEO_ADMISSION_UNCONFIRMED' });
    settleStudioVideoUsage(input.auth, id, { jobId: job.id });
    reconcileStudioVideoJob(input.auth, job);
  } else if ([400, 401, 403, 404, 405, 409, 413, 415, 422, 429].includes(response.status)) {
    settleStudioVideoUsage(input.auth, id, { release: true });
  }
  return response;
}
