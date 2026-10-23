import type { Request } from 'express';
import { assertGovernanceAccess, type AuthContext } from '../governance';
import { studioBridgeSecret, studioBridgeToken } from '../studios/proxy';
import type { KlicActor } from '../../src/klic/contracts';
import type { ChatMessage } from '../../src/klic/conversation';
import { KlicError } from './context';
type Reference = NonNullable<ChatMessage['production']>;
type Input = {
    req: Request;
    actor: KlicActor;
    instruction: string;
    requestId: string;
    previous?: Reference;
    signal: AbortSignal;
};
export function shouldUseLocalProduction(action: unknown, message: string, hasProject: boolean) {
    if (action === 'mode.local-production') return true;
    const text = message.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
    const create = /^(?:por favor[, ]*)?(?:crie|criar|gere|gerar|faca|produza|monte|quero (?:criar|um|uma)|gostaria de criar)\b/.test(text);
    const edit = /^(?:por favor[, ]*)?(?:mude|altere|troque|adicione|remova|anime|ajuste|deixe|aumente|reduza|faca|duplique|exclua|desfaca|desfazer)\b/.test(text);
    return create && (/\b(motion|video|imagem|cartao|cartaz)\b/.test(text) || action === 'create.video' || action === 'create.image')
        || hasProject && edit;
}
/** Same governance and signed Studios bridge as the existing BFF. No provider SDK. */
export async function prepareLocalProduction({ req, actor, instruction, requestId, previous, signal }: Input) {
    const selected = req.body.productionContext?.selected;
    const fromPage = selected?.kind === 'studio-document' && ['create-image', 'create-video'].includes(req.body.productionContext?.module)
        ? { documentId: selected.id, module: req.body.productionContext.module } : undefined;
    const reference = fromPage || previous;
    const selection: unknown = fromPage ? req.body.productionContext?.selectedLayerIds : undefined;
    if (selection !== undefined && (!Array.isArray(selection) || selection.length > 24
        || selection.some(id => typeof id !== 'string' || id.length > 120)))
        throw new KlicError('KLIC_INVALID_STUDIO_SELECTION');
    const selectedLayerIds = (selection || []) as string[];
    const module: 'create-image' | 'create-video' = reference?.module ||
        (/\b(imagem|cartaz|composi[çc][aã]o visual)\b/i.test(instruction) && !/\b(v[ií]deo|motion)\b/i.test(instruction) ? 'create-image' : 'create-video');
    const auth = (req as Request & {
        auth: AuthContext;
    }).auth;
    assertGovernanceAccess(auth, { module, clientId: actor.clientId, permission: reference ? 'content.edit' : 'content.create' });
    const origin = new URL(process.env.CLICKO_STUDIOS_ORIGIN || 'http://127.0.0.1:8000');
    const token = studioBridgeToken(auth, actor.clientId, module, studioBridgeSecret());
    async function call<T>(path: string, body?: unknown, key?: string): Promise<T> {
        const response = await fetch(new URL('/api/v1/studios/v1/' + path, origin), {
            method: body ? 'POST' : 'GET', signal,
            headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json',
                ...(key ? { 'Idempotency-Key': key } : {}) },
            ...(body ? { body: JSON.stringify(body) } : {}), redirect: 'error',
        });
        if (!response.ok)
            throw new KlicError('KLIC_LOCAL_STUDIO_UNAVAILABLE', response.status === 403 ? 403 : 503);
        const text = await response.text();
        if (text.length > 1000000)
            throw new KlicError('KLIC_LOCAL_STUDIO_RESULT_TOO_LARGE', 503);
        return JSON.parse(text) as T;
    }
    let document: {
        documentId: string;
        revision: number;
        title: string;
    };
    if (reference) {
        if (!/^[a-f0-9-]{36}$/.test(reference.documentId))
            throw new KlicError('KLIC_INVALID_STUDIO_DOCUMENT');
        document = await call('documents/' + reference.documentId);
    }
    else {
        const session = await call<{
            workspace: {
                id: string;
            };
        }>('bridge/session');
        document = await call('agents/projects', { workspaceId: session.workspace.id,
            title: instruction.slice(0, 100), contentType: module === 'create-video' ? 'video' : 'visual',
            width: 1280, height: 720 }, 'klic-create:' + requestId);
    }
    const task = await call<{
        id: string;
        status: string;
        errorCode?: string;
        result?: {
            commands?: unknown[];
            rationale?: string;
            inference?: string;
            planning?: string;
        };
    }>(`documents/${document.documentId}/agent-tasks`, { expectedRevision: document.revision, instruction, role: 'auto',
        ...(selectedLayerIds.length ? { selectedLayerIds } : {}) }, 'klic-plan:' + requestId);
    const url = `/studios/${module === 'create-video' ? 'video/motion' : 'image/edit'}?document=${document.documentId}`;
    const detail = task.status === 'failed' ? 'O planejamento não pôde ser concluído. Confira a configuração local no Studio.'
        : task.result?.rationale || 'Plano registrado no projeto.';
    const provenance = task.result?.inference === 'none' ? 'Planejamento por regras locais, sem inferência de IA.'
        : task.status === 'succeeded' ? 'Planejamento pelo modelo local configurado.' : '';
    const reply = `${detail}\n\n${provenance}\n\n${task.result?.commands?.length ? 'O plano está pronto para revisão e aplicação. ' : ''}` +
        `[Abrir projeto editável no Studio](${url}). Custo externo desta operação: R$ 0.`;
    return { reply, production: { documentId: document.documentId, module, taskId: task.id } as Reference };
}
