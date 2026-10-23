/** Functional audit using the running DEV server's own session. No mock/provider. */
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { DEV_CLIENT_ID, DEV_USER_ID, DEV_WORKSPACE_ID } from '../../src/development/contracts';

const root = path.resolve(import.meta.dirname, '../..');
process.chdir(root);
const profile = path.join(root, '.codex-runtime/clicko-dev');
const output = path.join(root, '.codex-runtime/audit-2026-10-23');
mkdirSync(output, { recursive: true });
const statusText = execFileSync(process.execPath, ['scripts/dev-local.mjs', 'status'], { encoding: 'utf8' }).trim();
assert.ok(statusText.startsWith('{'), 'Wait for the isolated DEV profile to be ready.');
const status = JSON.parse(statusText);
assert.equal(path.resolve(status.dataDirectory), profile); assert.equal(status.ready, true);
const origin = 'http://127.0.0.1:3018', base = '/api/v1/studios/v1';
const bootstrap = await fetch(origin + '/api/governance/auth/session', { signal: AbortSignal.timeout(60000) });
const actor = await bootstrap.json(); assert.equal(actor.user.id, DEV_USER_ID);
const cookie = bootstrap.headers.get('set-cookie')?.split(';')[0]; assert.ok(cookie);
const headers = { cookie, 'x-workspace-id': DEV_WORKSPACE_ID, 'x-clicko-client-id': DEV_CLIENT_ID, 'x-clicko-studio-module': 'create-video' };
const evidencePath = path.join(output, 'live.json');
type State = Record<string, any>;
const state: State = existsSync(evidencePath) ? JSON.parse(readFileSync(evidencePath, 'utf8')) : { run: randomUUID(), startedAt: new Date().toISOString(), tests: {}, assets: {} };
const persist = () => writeFileSync(evidencePath, JSON.stringify(state, null, 2));
const hash = (bytes: Uint8Array) => createHash('sha256').update(bytes).digest('hex');
async function call(route: string, body?: unknown, method = 'POST', key?: string) {
  const started = Date.now();
  let response: Response;
  try { response = await fetch(origin + route, { method: body === undefined ? 'GET' : method, signal: AbortSignal.timeout(180000),
    headers: { ...headers, ...(body instanceof FormData ? {} : { 'content-type': 'application/json' }), ...(key ? { 'Idempotency-Key': key } : {}) },
    body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body) }); }
  catch (error) { throw new Error(`${route}: transport ${error instanceof Error ? error.name : 'failure'}`, { cause: error }); }
  if (Date.now() - started > 10000) console.log(JSON.stringify({ route, status: response.status, elapsedMs: Date.now() - started }));
  if (!response.ok) assert.fail(`${route}: ${response.status} ${await response.text()}`);
  return response;
}
const json = async (route: string, body?: unknown, method?: string, key?: string) => (await call(route, body, method, key)).json();
const session = await json(base + '/bridge/session');
const workspace = session.workspace.id;
state.workspace = workspace;
const health = await json('/api/development/status'); assert.equal(health.costs.externalCallsEnabled, false);
state.runtime ||= { development: health, renderer: await json(base + '/video/capabilities'), roles: await json(base + `/agents/roles?workspace_id=${workspace}`),
  engines: await json(base + '/craft/engines'), imageAI: await json(base + '/editing/ai'), sceneGeneration: await json(base + '/scene-generation-capability') };
persist();
async function upload(file: string, mediaType: string) {
  if (state.assets[file]) return state.assets[file];
  const bytes = readFileSync(path.join(output, file));
  const form = new FormData(); form.set('workspace_id', workspace); form.set('title', 'AUDIT · ' + file);
  form.set('file', new Blob([bytes], { type: mediaType }), file);
  const asset = await json('/api/v1/assets/upload', form);
  assert.equal(asset.checksumSha256, hash(bytes)); state.assets[file] = asset; persist(); return asset;
}
async function download(url: string, file: string) {
  const bytes = Buffer.from(await (await call(url)).arrayBuffer());
  writeFileSync(path.join(output, file), bytes);
  return { file, downloadUrl: url, sha256: hash(bytes), bytes: bytes.length };
}
async function render(doc: any, file: string) {
  const key = `${state.run}:${file}`;
  const started = Date.now();
  let job = await json(`${base}/video/documents/${doc.documentId}/render-jobs`, { expectedRevision: doc.revision }, 'POST', key);
  const replay = await json(`${base}/video/documents/${doc.documentId}/render-jobs`, { expectedRevision: doc.revision }, 'POST', key);
  assert.equal(job.id, replay.id);
  const deadline = Date.now() + 900000;
  while (!['succeeded', 'failed', 'cancelled'].includes(job.status) && Date.now() < deadline) {
    await new Promise(resolve => setTimeout(resolve, 750)); job = await json(`${base}/jobs/${job.id}`);
  }
  assert.equal(job.status, 'succeeded', JSON.stringify(job));
  return { ...(await download(job.result.downloadUrl, file)), jobId: job.id, elapsedSeconds: (Date.now() - started) / 1000, revision: doc.revision };
}
const scope = { workspaceId: DEV_WORKSPACE_ID, clientId: DEV_CLIENT_ID, source: 'ai-chat' };
if (process.argv.includes('--verify')) {
  assert.notEqual(status.pid, state.serverPid, 'Restart the DEV supervisor before verification.');
  for (const entry of Object.values(state.tests) as any[]) {
    if (entry.documentId) {
      const doc = await json(`${base}/documents/${entry.documentId}`);
      assert.ok(doc.revision >= entry.revision);
      assert.equal(doc.workspaceId, workspace);
    }
    if (entry.delivery) assert.equal(hash(new Uint8Array(await (await call(entry.delivery.downloadUrl)).arrayBuffer())), entry.delivery.sha256);
  }
  for (const [file, asset] of Object.entries(state.assets) as [string, any][]) {
    assert.equal(hash(new Uint8Array(await (await call(`/api/v1/assets/${asset.id}/content`)).arrayBuffer())), hash(readFileSync(path.join(output, file))));
  }
  const conversation = await json('/api/klic/conversations/read', { ...scope, conversationId: state.conversationId });
  assert.ok(conversation.messages.length >= 4);
  state.persistenceVerifiedAt = new Date().toISOString(); persist();
  console.log(JSON.stringify({ persistence: 'passed', assetsPreserved: true, currentPid: status.pid }));
  process.exit(0);
}
if (!state.conversationId) { state.conversationId = (await json('/api/klic/conversations/create', scope)).id; persist(); }
async function command(instruction: string, selected: string[] = [], project?: string) {
  const requestId = randomUUID();
  const events = (await (await call('/api/klic/conversations/send', { ...scope, conversationId: state.conversationId, requestId,
    actionId: 'mode.local-production', message: instruction,
    ...(project ? { productionContext: { module: 'create-video', selected: { kind: 'studio-document', id: project }, selectedLayerIds: selected } } : {}) })).text())
    .trim().split('\n').map(line => JSON.parse(line));
  const answer = events.find(event => event.type === 'done')?.data.messages.at(-1);
  assert.ok(answer?.production, JSON.stringify(events));
  const task = await json(`${base}/documents/${answer.production.documentId}/agent-tasks/${answer.production.taskId}`);
  assert.equal(task.status, 'succeeded'); assert.equal(task.result.inference, 'none'); assert.equal(task.externalCostUsd, 0);
  return { answer, task };
}
if (!state.tests.A) {
  const conversation = await json('/api/klic/conversations/read', { ...scope, conversationId: state.conversationId });
  const previous = conversation.messages.at(-1)?.production;
  const result = previous ? { task: await json(`${base}/documents/${previous.documentId}/agent-tasks/${previous.taskId}`) }
    : await command('Crie um vídeo motion de 15 segundos sobre inovação e inteligência artificial, com três cenas, tipografia animada, elementos gráficos e transições fluidas.');
  const task = result.task;
  const doc = await json(`${base}/documents/${task.documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: task.documentRevision });
  assert.equal(doc.composition.narrative.localProduction.scenes.length, 3);
  assert.equal(doc.composition.pages[0].layers.length, 9);
  state.tests.A = { documentId: doc.documentId, revision: doc.revision, planning: task.result, manualApply: true, delivery: await render(doc, 'motion-a.mp4') };
  persist(); console.log('A: real 15s motion rendered; deterministic template, no model.');
}
if (!state.tests.C) {
  const documentId = state.tests.A.documentId;
  const records = state.edits || []; state.edits = records;
  const cases = [
    { instruction: 'Altere o título da segunda cena.', ids: [], targets: [], apply: false },
    { instruction: 'Altere o título da segunda cena para "Inteligência em movimento".', ids: [], targets: ['scene-2-title'], apply: true },
    { instruction: 'Deixe a transição mais suave.', ids: [], targets: [], apply: true },
    { instruction: 'Aumente a duração da primeira animação.', ids: ['scene-1-title'], targets: [], apply: false },
    { instruction: 'Mude a duração da animação para 4 segundos.', ids: ['scene-1-title'], targets: ['scene-1-title'], apply: true },
    { instruction: 'Troque a cor dos cartões.', ids: [], targets: [], apply: false },
    { instruction: 'Troque a cor dos cartões para tangerina.', ids: [], targets: ['scene-1-card', 'scene-2-card', 'scene-3-card'], apply: true },
    { instruction: 'Deixe a composição mais dinâmica.', ids: [], targets: [], apply: false },
    { instruction: 'Deixe a primeira cena mais dinâmica.', ids: [], targets: ['scene-1-card', 'scene-1-accent', 'scene-1-title'], apply: true },
    { instruction: 'Faça o texto aparecer palavra por palavra.', ids: ['scene-2-title'], targets: ['scene-2-title'], apply: true },
  ];
  for (const entry of cases.slice(records.length)) {
    const before = await json(`${base}/documents/${documentId}`);
    const { task } = await command(entry.instruction, entry.ids, documentId);
    let after = await json(`${base}/documents/${documentId}`);
    assert.equal(after.revision, before.revision, 'Planning must not mutate the document.');
    if (entry.apply) {
      assert.ok(task.result.commands.length, task.result.rationale);
      after = await json(`${base}/documents/${documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: before.revision });
      assert.deepEqual(after.composition.mediaTimeline, before.composition.mediaTimeline);
      for (const old of before.composition.pages[0].layers) {
        const latest = after.composition.pages[0].layers.find((layer: any) => layer.id === old.id);
        if (entry.targets.length && !entry.targets.includes(old.id)) assert.deepEqual(latest, old);
      }
    } else { assert.equal(task.result.commands.length, 0, task.result.rationale); assert.deepEqual(before.composition, after.composition); }
    records.push({ instruction: entry.instruction, applied: entry.apply, beforeRevision: before.revision, afterRevision: after.revision,
      commands: task.result.commands, explanation: task.result.rationale, inference: task.result.inference }); persist();
  }
  const doc = await json(`${base}/documents/${documentId}`);
  const versions = await json(`${base}/documents/${documentId}/versions`); assert.ok(versions.length >= 6);
  state.tests.C = { documentId, revision: doc.revision, versions: versions.length, delivery: await render(doc, 'motion-c.mp4') };
  assert.equal(hash(new Uint8Array(await (await call(state.tests.A.delivery.downloadUrl)).arrayBuffer())), state.tests.A.delivery.sha256);
  persist(); console.log('C: edits, clarification, scope and old delivery preserved.');
}
if (!state.tests.C2) {
  // The earlier numeric retiming case shortened 5 s to 4 s. Test a genuine
  // increase separately, preserving both earlier deliveries and their evidence.
  const documentId = state.tests.C.documentId;
  const before = await json(`${base}/documents/${documentId}`);
  const title = before.composition.pages[0].layers.find((layer: any) => layer.id === 'scene-1-title');
  assert.equal(title.properties.durationFrames, 96);
  const { task } = await command('Aumente a duração da primeira animação para 5 segundos.', ['scene-1-title'], documentId);
  assert.ok(task.result.commands.length);
  const doc = await json(`${base}/documents/${documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: before.revision });
  assert.equal(doc.composition.pages[0].layers.find((layer: any) => layer.id === title.id).properties.durationFrames, 120);
  for (const old of before.composition.pages[0].layers) {
    if (old.id !== title.id) assert.deepEqual(doc.composition.pages[0].layers.find((layer: any) => layer.id === old.id), old);
  }
  const versions = await json(`${base}/documents/${documentId}/versions`);
  state.tests.C2 = { documentId, revision: doc.revision, versions: versions.length, durationFramesFrom: 96, durationFramesTo: 120,
    delivery: await render(doc, 'motion-c2.mp4') };
  for (const old of [state.tests.A, state.tests.C]) {
    assert.equal(hash(new Uint8Array(await (await call(old.delivery.downloadUrl)).arrayBuffer())), old.delivery.sha256);
  }
  persist(); console.log('C2: actual 4-to-5-second increase, other layers and previous deliveries preserved.');
}
const sources = [await upload('source-red-blue.mp4', 'video/mp4'), await upload('source-tone.wav', 'audio/wav'), await upload('source-card.png', 'image/png')];
if (!state.tests.B) {
  const range = (startFrame: number, durationFrames: number) => ({ startFrame, durationFrames });
  const tracks = [
    { id: 'video', name: 'Reordered clips', kind: 'video', clips: [
      { id: 'blue-first', assetId: sources[0].id, timeline: range(0, 48), source: { startMicroseconds: 2000000, durationMicroseconds: 2000000 }, transform: { originalAudioEnabled: false, fadeInFrames: 6, fadeOutFrames: 6 } },
      { id: 'red-second', assetId: sources[0].id, timeline: range(48, 48), source: { startMicroseconds: 0, durationMicroseconds: 2000000 }, transform: { originalAudioEnabled: false, fadeInFrames: 6, fadeOutFrames: 6 } },
    ] },
    { id: 'overlay', name: 'Own graphic', kind: 'overlay', clips: [{ id: 'card', assetId: sources[2].id, timeline: range(0, 96), transform: { scale: 0.25, x: 420, y: -230 } }] },
    { id: 'titles', name: 'Editable caption', kind: 'caption', cues: [{ id: 'title', text: 'Auditoria Clicko', timeline: range(0, 96),
      style: { fontFamily: 'system', fontSize: 44, color: '#FFFFFF', outlineWidth: 2, maxLines: 2 }, motion: { fadeInFrames: 6, fadeOutFrames: 6 },
      keyframes: [{ property: 'y', frame: 0, value: 20 }, { property: 'y', frame: 12, value: 0 }] }] },
    { id: 'audio', name: 'Own tone -6dB and fades', kind: 'audio', clips: [{ id: 'tone', assetId: sources[1].id, timeline: range(0, 96), gainDb: -6, fadeInFrames: 12, fadeOutFrames: 12 }] },
  ];
  const known = (await json(`${base}/documents?workspace_id=${workspace}`)).find((row: any) => row.correlationId === state.run + '-B');
  let doc = known || await json(base + '/documents', { workspaceId: workspace, title: 'AUDIT · Montagem, cortes e áudio', contentType: 'video', brandRevision: 1,
    brief: { objective: 'Prova real de montagem audiovisual', audience: 'Equipe de desenvolvimento', format: 'video' }, correlationId: state.run + '-B',
    composition: { pages: [{ id: 'page-1', width: 1280, height: 720, background: '#000000', durationMs: 6000, layers: [] }],
      narrative: {}, mediaTimeline: { durationFrames: 144, frameRate: { numerator: 24, denominator: 1 }, tracks: [] } },
    assets: sources.map(asset => ({ id: asset.id, mediaType: asset.mediaType, checksum: asset.checksumSha256, origin: 'workspace', rightsStatus: 'unknown' })) });
  const timeline = { schemaVersion: 'studio.media-timeline.v1', durationFrames: 96, frameRate: { numerator: 24, denominator: 1 }, tracks };
  if (doc.revision === 1) doc = await json(`${base}/video/documents/${doc.documentId}/timeline`, { expectedRevision: doc.revision, timeline }, 'PUT', state.run + '-B-edit');
  state.pendingBDocumentId = doc.documentId; persist();
  state.tests.B = { documentId: doc.documentId, revision: doc.revision, durationChangedFrom: 6, durationChangedTo: 4,
    cutReordered: true, transitions: 'per-clip fades, not advanced cross-transitions', delivery: await render(doc, 'video-b.mp4') }; persist();
  console.log('B: real reordered cuts, caption, image overlay, gain/fades rendered.');
}
if (!state.tests.I) {
  headers['x-clicko-studio-module'] = 'create-image';
  let doc = await json(`${base}/agents/projects`, { workspaceId: workspace, title: 'AUDIT · Composição visual', contentType: 'visual', width: 1280, height: 720 }, 'POST', state.run + '-I');
  const shape = { id: 'shape', kind: 'shape', name: 'Gradiente local', x: 80, y: 80, width: 1120, height: 560, opacity: 1, rotation: 0, visible: true, locked: false, zIndex: 0,
    properties: { schemaVersion: 'studio.local-layer.v1', fill: '#161616', gradientEnd: '#303030', radius: 24, shadow: true } };
  const image = { ...shape, id: 'image', kind: 'image', name: 'Material preservado', x: 100, y: 100, width: 400, height: 240, zIndex: 1,
    properties: { schemaVersion: 'studio.local-layer.v1', assetId: sources[2].id, crop: { x: 0.1, y: 0.1, width: 0.8, height: 0.8 }, brightness: 1.1, contrast: 1.05, saturation: 0.9 } };
  const text = { ...shape, id: 'text', kind: 'text', name: 'Texto editável', x: 100, y: 390, width: 1000, height: 140, zIndex: 2,
    properties: { schemaVersion: 'studio.local-layer.v1', text: 'Inovação com a Clicko', fontSize: 64, fontFamily: 'system', color: '#FFFFFF' } };
  doc = await json(`${base}/documents/${doc.documentId}/local-commands`, { expectedRevision: doc.revision, commands: [
    { id: 'asset.attach', params: { assetId: sources[2].id } },
    ...[shape, image, text].map(layer => ({ id: 'layer.upsert', params: { layer } })),
  ] }, 'POST', state.run + '-I-edit');
  const exported = await json(`${base}/documents/${doc.documentId}/local-image-export`, { expectedRevision: doc.revision }, 'POST', state.run + '-I-export');
  state.tests.I = { documentId: doc.documentId, revision: doc.revision, originalPreserved: true, delivery: await download(exported.downloadUrl, 'image-i.png') }; persist();
}
for (const [file, asset] of Object.entries(state.assets) as [string, any][]) {
  assert.equal(hash(new Uint8Array(await (await call(`/api/v1/assets/${asset.id}/content`)).arrayBuffer())), hash(readFileSync(path.join(output, file))));
}
state.serverPid = status.pid;
state.summary = { realDevSession: true, realBackendAndRender: true, mockProvider: false, modelInference: false, externalCostUsd: 0,
  creationA: true, editingB: true, contextualC: true, imageI: true, sourceChecksumsUnchanged: true,
  browserQa: 'blocked by Work browser-use setting', inferenceAndGeneration: 'not tested; no available authorized model' };
state.completedAt = new Date().toISOString(); persist(); console.log(JSON.stringify(state.summary));
