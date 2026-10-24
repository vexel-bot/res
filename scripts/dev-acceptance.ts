/** Real DEV-session acceptance; no fixture identity, direct SQL, mock, or provider call.
 * Creates only named test projects in the marked private DEV profile.
 * Run once, restart dev:local, then run with --verify for read-only recovery checks.
 */
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { DEV_WORKSPACE_ID, DEV_USER_ID, DEV_CLIENT_ID } from '../src/development/contracts';
import { initialVideoBrief, videoDocumentInput } from '../src/studios/video/videoModel';
import { patchItem, type Timeline } from '../src/studios/video/canonicalTimeline';

const root = path.resolve(import.meta.dirname, '..');
process.chdir(root);
const profile = path.join(root, '.codex-runtime/clicko-dev');
const statusText = execFileSync(process.execPath, ['scripts/dev-local.mjs', 'status'], { encoding: 'utf8' }).trim();
assert.ok(statusText.startsWith('{'), 'DEV is still starting or unavailable. Wait for dev:status ready before acceptance.');
const status = JSON.parse(statusText);
assert.equal(path.resolve(status.dataDirectory), profile);
assert.equal(status.ready, true);
const marker = JSON.parse(readFileSync(path.join(profile, 'dev-profile.json'), 'utf8'));
assert.equal(marker.schemaVersion, 'clicko.local-dev.v1');
const origin = 'http://127.0.0.1:3018';
const session = await fetch(origin + '/api/governance/auth/session');
assert.equal(session.status, 200);
const cookie = session.headers.get('set-cookie')?.split(';')[0];
assert.ok(cookie?.startsWith('clicko_dev_session='));
const actor = await session.json();
assert.equal(actor.user.id, DEV_USER_ID);
assert.equal(actor.development.workspaceId, DEV_WORKSPACE_ID);
const headers = { cookie, 'x-workspace-id': DEV_WORKSPACE_ID, 'x-clicko-client-id': DEV_CLIENT_ID,
  'x-clicko-studio-module': 'create-video' };
async function request(route: string, body?: unknown, method = 'POST', key: string = randomUUID()): Promise<Response> {
  const response = await fetch(origin + route, { method: body === undefined ? 'GET' : method,
    headers: { ...headers, ...(body instanceof FormData ? {} : { 'content-type': 'application/json' }),
      ...(body === undefined ? {} : { 'Idempotency-Key': key }) },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body) });
  assert.ok(response.ok, `${route}: ${response.status} ${await response.clone().text()}`);
  return response;
}
const json = async (route: string, body?: unknown, method?: string, key?: string) =>
  (await request(route, body, method, key)).json();
const base = '/api/v1/studios/v1';
const bridge = await json(base + '/bridge/session');
const studioWorkspaceId = bridge.workspace.id as string;
assert.equal(studioWorkspaceId, status.health.development.studioWorkspaceId);
const health = await json('/api/development/status');
assert.equal(health.costs.externalCallsEnabled, false);
assert.equal(health.costs.externalBudgetUsd, 0);
assert.equal(health.services.bridge, true);
const evidenceFile = path.join(profile, 'live-acceptance.json');
const hash = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex');
async function download(url: string, file: string) {
  const bytes = Buffer.from(await (await request(url)).arrayBuffer());
  writeFileSync(path.join(profile, file), bytes);
  return { url, file, bytes: bytes.length, sha256: hash(bytes) };
}

if (process.argv.includes('--verify')) {
  const evidence = JSON.parse(readFileSync(evidenceFile, 'utf8'));
  assert.notEqual(status.pid, evidence.serverPid, 'Restart dev:local before verifying persistence.');
  assert.equal(evidence.studioWorkspaceId, studioWorkspaceId);
  for (const entry of evidence.documents) {
    const doc = await json(`${base}/documents/${entry.documentId}`);
    assert.equal(doc.workspaceId, studioWorkspaceId);
    assert.equal(doc.revision, entry.revision);
    assert.equal(hash(Buffer.from(JSON.stringify(doc.composition))), entry.compositionHash);
  }
  for (const entry of evidence.deliveries) {
    const bytes = new Uint8Array(await (await request(entry.url)).arrayBuffer());
    assert.equal(hash(bytes), entry.sha256);
  }
  const conversations = await json('/api/klic/conversations/read', { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID,
    source: 'ai-chat', conversationId: evidence.conversationId });
  assert.ok(JSON.stringify(conversations).includes(evidence.klicTaskId));
  evidence.persistenceVerifiedAt = new Date().toISOString();
  writeFileSync(evidenceFile, JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify({ persistence: true, documents: evidence.documents.length, deliveries: evidence.deliveries.length,
    reservedWorkspace: true, costsEnabled: false }));
} else if (process.argv.includes('--recover-final')) {
  // Recover the already completed run if collecting a delivery was interrupted.
  // Only read requests and downloads: no duplicate uploads, edits, jobs or plans.
  const rows = await json(`${base}/documents?workspace_id=${studioWorkspaceId}`);
  const titles = ['DEV · Homologação Motion 15s', 'DEV · Composição de imagem', 'DEV · Edição de vídeo validada por API'];
  const documents = [];
  for (const title of titles) {
    const matches = rows.filter((row: { title: string }) => row.title === title);
    assert.equal(matches.length, 1);
    documents.push(await json(`${base}/documents/${matches[0].documentId}`));
  }
  const videoDoc = documents[2];
  const jobs = await json(`${base}/jobs?workspace_id=${studioWorkspaceId}&document_id=${videoDoc.documentId}`);
  const render = jobs.find((job: { status: string }) => job.status === 'succeeded');
  assert.ok(render);
  const conversations = await json('/api/klic/conversations/list', { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID, source: 'ai-chat' });
  assert.equal(conversations.conversations.length, 1);
  const conversation = await json('/api/klic/conversations/read', { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID,
    source: 'ai-chat', conversationId: conversations.conversations[0].id });
  const answer = conversation.messages.at(-1);
  const task = await json(`${base}/documents/${documents[0].documentId}/agent-tasks/${answer.production.taskId}`);
  assert.equal(task.result.inference, 'none'); assert.equal(task.externalCostUsd, 0);
  const sourceBytes = new Uint8Array(await (await request(`/api/v1/assets/${videoDoc.assets[0].id}/content`)).arrayBuffer());
  assert.equal(hash(sourceBytes), hash(readFileSync(path.join(root, '.codex-runtime/stage3-shared-media/video-source.mp4'))));
  const deliveries = [await download(render.result.downloadUrl, 'technical-video.mp4'),
    await download('/api/v1/assets/e3654f61-8d1d-41b0-896d-ccb020fb0b5f/content', 'ui-motion.mp4'),
    await download('/api/v1/assets/35ee9ca7-9719-4837-ac5f-b80c8f150a67/content', 'ui-image.png')];
  writeFileSync(evidenceFile, JSON.stringify({ createdAt: new Date().toISOString(), mode: 'real_server_issued_dev_session', profile, serverPid: status.pid,
    studioWorkspaceId, recoveredAfterDeliveryRouteCorrection: true, videoBrowserQa: false, klicBrowserQa: false,
    browserBlocker: 'Browser use disabled in Work settings', source: { assetId: videoDoc.assets[0].id, sha256: hash(sourceBytes) },
    conversationId: conversation.id, klicTaskId: task.id, inference: 'none', externalCostUsd: 0,
    renderJobId: render.id, deliveries, documents: documents.map(row => ({ documentId: row.documentId, title: row.title,
      revision: row.revision, compositionHash: hash(Buffer.from(JSON.stringify(row.composition))) })) }, null, 2));
  console.log(JSON.stringify({ recovered: true, documents: documents.length, deliveries: deliveries.length }));
} else {
  // Refuse an accidental second creation run; --verify is non-mutating.
  const { existsSync } = await import('node:fs');
  assert.equal(existsSync(evidenceFile), false, 'Acceptance already created. Use --verify; do not duplicate projects.');
  const sourceFile = path.join(root, '.codex-runtime/stage3-shared-media/video-source.mp4');
  const sourceBytes = readFileSync(sourceFile);
  const form = new FormData();
  form.set('workspace_id', studioWorkspaceId); form.set('title', 'DEV · Material de vídeo próprio');
  form.set('tags', 'dev,qa,source'); form.set('file', new Blob([sourceBytes], { type: 'video/mp4' }), 'video-source.mp4');
  const asset = await json('/api/v1/assets/upload', form);
  const sourceHash = hash(sourceBytes);
  assert.equal(asset.checksumSha256, sourceHash);
  const probe = await json(`${base}/video/assets/${asset.id}/probe?workspace_id=${studioWorkspaceId}`);
  assert.ok(probe.durationSeconds >= 3);
  const brief = { ...initialVideoBrief(), title: 'DEV · Edição de vídeo validada por API',
    objective: 'Montagem e corte de material próprio sem geração externa', audience: 'Equipe de desenvolvimento',
    script: 'Prova local de importação, corte e exportação.', aspect: '16:9' as const, duration: 3 };
  let doc = await json(base + '/documents', videoDocumentInput(studioWorkspaceId, brief, [asset]));
  let timeline = structuredClone(doc.composition.mediaTimeline) as Timeline;
  timeline = patchItem(timeline, 'clip-1', clip => ({ ...clip,
    source: { startMicroseconds: 1_000_000, durationMicroseconds: 3_000_000 },
    transform: { ...clip.transform, originalAudioEnabled: false, opacity: 0.9 } }));
  const edit = { expectedRevision: doc.revision, timeline }, editKey = randomUUID();
  doc = await json(`${base}/video/documents/${doc.documentId}/timeline`, edit, 'PUT', editKey);
  const replay = await json(`${base}/video/documents/${doc.documentId}/timeline`, edit, 'PUT', editKey);
  assert.equal(replay.revision, doc.revision);
  let job = await json(`${base}/video/documents/${doc.documentId}/render-jobs`, { expectedRevision: doc.revision });
  const deadline = Date.now() + 180_000;
  while (!['succeeded', 'failed', 'cancelled'].includes(job.status) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 500));
    job = await json(`${base}/jobs/${job.id}`);
  }
  assert.equal(job.status, 'succeeded', JSON.stringify(job));
  const video = await download(job.result.downloadUrl, 'technical-video.mp4');
  assert.equal(hash(new Uint8Array(await (await request(`/api/v1/assets/${asset.id}/content`)).arrayBuffer())), sourceHash);
  const documents = await json(`${base}/documents?workspace_id=${studioWorkspaceId}`);
  const motion = documents.find((row: { title: string }) => row.title === 'DEV · Homologação Motion 15s');
  const image = documents.find((row: { title: string }) => row.title === 'DEV · Composição de imagem');
  assert.ok(motion && image, 'Preserve and recover the projects created in the actual browser session.');
  const before = await json(`${base}/documents/${motion.documentId}`);
  const conversation = await json('/api/klic/conversations/create', { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID, source: 'ai-chat' });
  const send = { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID, source: 'ai-chat', conversationId: conversation.id,
    requestId: randomUUID(), actionId: 'mode.local-production', message: 'Mude a cor do título selecionado para tangerina',
    productionContext: { module: 'create-video', selected: { kind: 'studio-document', id: before.documentId }, selectedLayerIds: ['scene-1-title'] } };
  const events = (await (await request('/api/klic/conversations/send', send)).text()).trim().split('\n').map(line => JSON.parse(line));
  const answer = events.find(event => event.type === 'done')?.data.messages.at(-1);
  assert.ok(answer?.production, JSON.stringify(events));
  assert.equal(answer.production.documentId, before.documentId);
  const task = await json(`${base}/documents/${before.documentId}/agent-tasks/${answer.production.taskId}`);
  assert.equal(task.status, 'succeeded'); assert.equal(task.result.inference, 'none'); assert.equal(task.externalCostUsd, 0);
  const applied = await json(`${base}/documents/${before.documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: before.revision });
  for (const layer of before.composition.pages[0].layers) {
    const latest = applied.composition.pages[0].layers.find((row: { id: string }) => row.id === layer.id);
    if (layer.id === 'scene-1-title') assert.equal(latest.properties.color, '#F28500');
    else assert.deepEqual(latest, layer);
  }
  const again = await json(`${base}/documents/${before.documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: before.revision });
  assert.equal(again.revision, applied.revision);
  const deliveries = [video];
  for (const [id, file] of [['e3654f61-8d1d-41b0-896d-ccb020fb0b5f', 'ui-motion.mp4'], ['35ee9ca7-9719-4837-ac5f-b80c8f150a67', 'ui-image.png']])
    deliveries.push(await download(`/api/v1/assets/${id}/content`, file));
  const persisted = [applied, await json(`${base}/documents/${image.documentId}`), await json(`${base}/documents/${doc.documentId}`)];
  const evidence = { createdAt: new Date().toISOString(), mode: 'real_server_issued_dev_session', profile, serverPid: status.pid, studioWorkspaceId,
    videoBrowserQa: false, klicBrowserQa: false, browserBlocker: 'Browser use disabled in Work settings',
    source: { assetId: asset.id, sha256: sourceHash }, conversationId: conversation.id, klicTaskId: task.id,
    inference: 'none', externalCostUsd: 0, renderJobId: job.id, deliveries,
    documents: persisted.map(row => ({ documentId: row.documentId, title: row.title, revision: row.revision,
      compositionHash: hash(Buffer.from(JSON.stringify(row.composition))) })) };
  writeFileSync(evidenceFile, JSON.stringify(evidence, null, 2));
  console.log(JSON.stringify({ realDevSession: true, imported: true, trimmed: true, rendered: true, videoDocumentId: doc.documentId,
    klicContext: true, klicApplied: true, idempotent: true, externalCostUsd: 0 }));
}
