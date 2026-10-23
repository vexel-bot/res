import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createGovernanceRouter } from '../governance';
import { createKlicRuntime } from './router';
import { ConversationStore } from './conversations';
import { KlicMemory } from './store';
import { shouldUseLocalProduction } from './localProduction';

test('KLIC routes explicit creation and in-project editing while leaving informational questions to conversation', () => {
    assert.equal(shouldUseLocalProduction('create.general', 'Crie um motion de 30 segundos', false), true);
    assert.equal(shouldUseLocalProduction('create.general', 'Mude a cor para #6EB8F5', true), true);
    assert.equal(shouldUseLocalProduction('create.general', 'Qual a diferença entre vídeo e motion?', false), false);
    assert.equal(shouldUseLocalProduction('create.general', 'Mude a cor para #6EB8F5', false), false);
    assert.equal(shouldUseLocalProduction('create.general', 'Faça o texto aparecer palavra por palavra', true), true);
    assert.equal(shouldUseLocalProduction('create.general', 'Aumente a duração para 20 segundos', true), true);
    assert.equal(shouldUseLocalProduction('create.general', 'Desfaça a última alteração.', true), true);
    assert.equal(shouldUseLocalProduction('create.general', 'Desfaça a última alteração.', false), false);
});
test('KLIC local production uses its existing conversation and signed Studio authority without a paid provider', async (t) => {
    const folder = mkdtempSync(path.join(tmpdir(), 'clicko-agent-test-'));
    const oldOrigin = process.env.CLICKO_STUDIOS_ORIGIN, oldKey = process.env.CLICKO_STUDIOS_BRIDGE_SECRET;
    const documentId = randomUUID(), taskId = randomUUID();
    let created = 0, planned = 0, paid = 0;
    const selections: string[][] = [];
    const studio = express();
    studio.use(express.json());
    studio.use((req, _res, next) => {
        const token = req.header('authorization')?.split(' ')[1];
        assert.ok(token);
        const claims = JSON.parse(Buffer.from(token!.split('.')[1], 'base64url').toString());
        assert.equal(claims.sub, 'usr-master');
        assert.equal(claims.module, 'create-video');
        assert.equal(claims.aud, 'clicko-studios');
        next();
    });
    studio.get('/api/v1/studios/v1/bridge/session', (_req, res) => res.json({ workspace: { id: 'qa-workspace' } }));
    studio.post('/api/v1/studios/v1/agents/projects', (req, res) => { created++; assert.equal(req.body.workspaceId, 'qa-workspace'); assert.match(req.header('idempotency-key') || '', /^klic-create:/); res.status(201).json({ documentId, revision: 1, title: 'Motion' }); });
    studio.get('/api/v1/studios/v1/documents/:id', (_req, res) => res.json({ documentId, revision: 2, title: 'Motion' }));
    studio.post('/api/v1/studios/v1/documents/:id/agent-tasks', (req, res) => { planned++; selections.push(req.body.selectedLayerIds || []); assert.match(req.header('idempotency-key') || '', /^klic-plan:/); assert.equal(req.body.role, 'auto'); res.json({ id: taskId, status: 'succeeded', result: { commands: [{ id: 'layer.upsert' }], inference: 'none', rationale: 'Planejamento local de teste.' } }); });
    const upstream = studio.listen(0, '127.0.0.1');
    await new Promise<void>(resolve => upstream.once('listening', resolve));
    process.env.CLICKO_STUDIOS_ORIGIN = `http://127.0.0.1:${(upstream.address() as {
        port: number;
    }).port}`;
    process.env.CLICKO_STUDIOS_BRIDGE_SECRET = 'agent-test-key-at-least-32-characters';
    const app = express();
    app.use(express.json());
    app.use('/governance', createGovernanceRouter({ dataFile: null }));
    const runtime = createKlicRuntime({ memory: new KlicMemory(null), conversations: new ConversationStore(folder), conversationProvider: {
            async *stream() { paid++; yield 'Should not run'; }, async transcribe() { paid++; return 'Should not run'; },
        } });
    app.use('/api/klic', runtime.router);
    const server = app.listen(0, '127.0.0.1');
    await new Promise<void>(resolve => server.once('listening', resolve));
    t.after(async () => {
        await new Promise<void>(resolve => server.close(() => resolve()));
        await new Promise<void>(resolve => upstream.close(() => resolve()));
        if (oldOrigin === undefined)
            delete process.env.CLICKO_STUDIOS_ORIGIN;
        else
            process.env.CLICKO_STUDIOS_ORIGIN = oldOrigin;
        if (oldKey === undefined)
            delete process.env.CLICKO_STUDIOS_BRIDGE_SECRET;
        else
            process.env.CLICKO_STUDIOS_BRIDGE_SECRET = oldKey;
        rmSync(folder, { recursive: true, force: true });
    });
    const origin = `http://127.0.0.1:${(server.address() as {
        port: number;
    }).port}`;
    const headers = { 'Content-Type': 'application/json', 'x-workspace-id': 'ws-1', 'x-user-id': 'usr-master' };
    const post = (route: string, body: unknown) => fetch(`${origin}/api/klic/${route}`, { method: 'POST', headers, body: JSON.stringify({ workspaceId: 'ws-1', clientId: null, source: 'ai-chat', ...body as object }) });
    const conversation = await (await post('conversations/create', {})).json();
    assert.ok(conversation.id);
    const requestId = randomUUID();
    const input = { conversationId: conversation.id, requestId, actionId: 'mode.local-production', message: 'Crie um motion design de 12 segundos' };
    const response = await post('conversations/send', input);
    assert.equal(response.status, 200);
    const events = (await response.text()).trim().split('\n').map(line => JSON.parse(line));
    const done = events.find(event => event.type === 'done');
    assert.ok(done, JSON.stringify(events));
    const answer = done.data.messages.at(-1);
    assert.equal(answer.production.documentId, documentId);
    assert.match(answer.content, /sem inferência/);
    assert.match(answer.content, /R\$ 0/);
    assert.match(answer.content, /document=/);
    assert.equal(paid, 0);
    assert.equal(created, 1);
    assert.equal(planned, 1);
    assert.equal((await post('conversations/send', input)).status, 200);
    assert.equal(planned, 1);
    const next = await post('conversations/send', { ...input, requestId: randomUUID(), message: 'Altere a cor para #6EB8F5',
        productionContext:{module:'create-video',selected:{kind:'studio-document',id:documentId},selectedLayerIds:['scene-2-title']} });
    await next.text();
    assert.equal(created, 1);
    assert.equal(planned, 2);
    assert.equal(paid, 0);
    assert.deepEqual(selections, [[], ['scene-2-title']]);
});
