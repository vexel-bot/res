import { createHash } from 'node:crypto';
import { hasPermission } from '../../src/security/accessControl';
import type { KlicActor, KlicRecord, KlicRequest } from '../../src/klic/contracts';
import type { KlicCore } from './core';
import { KlicError } from './context';

const safeText = (value: unknown, limit: number) => typeof value === 'string' ? value.trim().slice(0, limit) : '';
const externalOrCritical = new Set([
  'publication.publish.request', 'publication.schedule.request', 'approvals.submit.request', 'automations.start.request',
  'connections.disconnect.request', 'team.access.request', 'subscription.change.request', 'resource.delete.request',
]);

/**
 * Prepares reversible internal work using a stable, audited contract. It never
 * publishes, schedules, disconnects or changes access. Those actions remain in
 * their owning services and require their own confirmation boundary.
 */
export function prepareKlicAction(core: KlicCore, actor: KlicActor, request: KlicRequest, actionId: string, idempotencyKey: string, input: unknown) {
  const task = core.task(actor, request);
  if (!/^[A-Za-z0-9:_-]{8,160}$/.test(idempotencyKey)) throw new KlicError('KLIC_INVALID_IDEMPOTENCY_KEY');
  if (externalOrCritical.has(actionId)) throw new KlicError('KLIC_CONFIRMATION_REQUIRED', 409);
  if (!hasPermission(actor.user, 'content.create')) throw new KlicError('KLIC_PERMISSION_DENIED', 403);
  if (!input || typeof input !== 'object') throw new KlicError('KLIC_ACTION_INPUT_INVALID');
  const values = input as Record<string, unknown>;
  const title = safeText(values.title, 160);
  if (!title) throw new KlicError('KLIC_ACTION_INPUT_INVALID');
  let resource: KlicRecord;
  if (actionId === 'calendar.draft.prepare') {
    const scheduledAt = safeText(values.scheduledAt, 40);
    if (scheduledAt && (!Number.isFinite(Date.parse(scheduledAt)) || Date.parse(scheduledAt) <= Date.now())) throw new KlicError('KLIC_SCHEDULE_INVALID');
    const platform = safeText(values.platform, 40) || 'instagram';
    const format = safeText(values.format, 40) || 'post';
    if (!['instagram', 'facebook', 'linkedin', 'tiktok', 'youtube', 'x', 'threads', 'pinterest'].includes(platform)
      || !['post', 'carousel', 'story', 'reels', 'video', 'short', 'text'].includes(format)) throw new KlicError('KLIC_ACTION_INPUT_INVALID');
    resource = {
      workspaceId: actor.workspaceId, clientId: actor.clientId,
      id: `klic-draft-${createHash('sha256').update(idempotencyKey).digest('hex').slice(0, 20)}`,
      type: 'calendar-draft', title, copy: safeText(values.copy, 20_000), platform, format,
      status: 'draft', ...(scheduledAt ? { scheduledAt } : {}), preparedBy: 'klic',
    };
  } else if (actionId === 'content.draft.prepare') {
    const destination = safeText(values.destination, 40) || 'create-copy';
    if (!['create-copy', 'create-image', 'create-video', 'library'].includes(destination)) throw new KlicError('KLIC_ACTION_INPUT_INVALID');
    resource = {
      workspaceId: actor.workspaceId, clientId: actor.clientId,
      id: `klic-content-${createHash('sha256').update(idempotencyKey).digest('hex').slice(0, 20)}`,
      type: 'content-draft', title, brief: safeText(values.brief, 20_000), destination,
      status: 'draft', preparedBy: 'klic',
    };
  } else throw new KlicError('KLIC_UNKNOWN_ACTION', 404);
  const action = core.memory.prepareAction(actor, idempotencyKey, actionId, resource);
  core.memory.trace({ workspaceId: actor.workspaceId, userId: actor.userId, clientId: actor.clientId, parentId: task.traceId, origin: request.source, tool: actionId, status: 'ok', durationMs: 0, recordCount: 1 });
  return { ...action, traceId: task.traceId };
}
