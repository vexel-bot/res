import { apiFetch, apiFetchBlob } from '../../api';
import type { CraftDocument } from '../craft/craftApi';
import type { Timeline } from '../video/canonicalTimeline';
export type LocalKey = {
    property: 'x' | 'y' | 'scale' | 'rotation' | 'opacity';
    frame: number;
    value: number;
    easing?: 'linear' | 'ease-out' | 'ease-in-out';
};
export type LocalStyle = {
    schemaVersion: 'studio.local-layer.v1';
    text?: string;
    fontSize?: number;
    fontFamily?: 'system' | 'Liberation Sans';
    fontWeight?: 400 | 700;
    textReveal?: 'all' | 'words';
    wordStaggerFrames?: number;
    color?: string;
    fill?: string;
    gradientEnd?: string | null;
    shape?: 'rectangle' | 'ellipse';
    radius?: number;
    align?: 'left' | 'center' | 'right';
    shadow?: boolean;
    assetId?: string;
    brightness?: number;
    contrast?: number;
    saturation?: number;
    crop?: {
        x: number;
        y: number;
        width: number;
        height: number;
    } | null;
    startFrame?: number;
    durationFrames?: number | null;
    keyframes?: LocalKey[];
};
export type LocalLayer = {
    id: string;
    kind: 'text' | 'shape' | 'image';
    name: string;
    x: number;
    y: number;
    width: number;
    height: number;
    rotation: number;
    opacity: number;
    visible: boolean;
    locked: boolean;
    zIndex: number;
    properties: LocalStyle;
};
type LocalPage = Omit<CraftDocument['composition']['pages'][number], 'layers'> & {
    layers: LocalLayer[];
};
export type LocalDocument = Omit<CraftDocument, 'composition'> & {
    composition: Omit<CraftDocument['composition'], 'pages' | 'mediaTimeline'> & {
        pages: LocalPage[];
        mediaTimeline?: Timeline | null;
    };
};
export type LocalOperation = {
    id: 'layer.upsert' | 'layer.remove' | 'project.background' | 'project.duration' | 'timeline.replace' | 'asset.attach' | 'composition.replace';
    params: Record<string, unknown>;
};
export type AgentTask = {
    id: string;
    documentId: string;
    documentRevision: number;
    status: string;
    role: string;
    provider: string;
    model?: string;
    errorCode?: string;
    requestedBy?: string;
    instruction?: string;
    appliedRevision?: number | null;
    createdAt?: string;
    history?: { type: string; at: string; actorId: string; detail: Record<string, unknown> }[];
    result?: {
        commands: LocalOperation[];
        rationale: string;
        state: string;
        inference: string;
        planning?: string;
    };
};
export type RoleBinding = {
    mode: 'local_tools' | 'local_model';
    connectionId?: string | null;
    model?: string | null;
};
export type AgentRoles = {
    revision: number;
    audiovisual: RoleBinding;
    image: RoleBinding;
};
export const localBase = '/api/v1/studios/v1';
const post = (body: unknown, key?: string): RequestInit => ({ method: 'POST', body: JSON.stringify(body),
    headers: key ? { 'Idempotency-Key': key } : undefined });
export const localApi = {
    create: (body: unknown, key: string) => apiFetch<LocalDocument>(`${localBase}/agents/projects`, post(body, key)),
    document: (id: string) => apiFetch<LocalDocument>(`${localBase}/documents/${encodeURIComponent(id)}`),
    list: (workspace: string, signal?: AbortSignal) => apiFetch<LocalDocument[]>(`${localBase}/documents?workspace_id=${encodeURIComponent(workspace)}`, { signal }),
    roles: (workspace: string, signal?: AbortSignal) => apiFetch<AgentRoles>(`${localBase}/agents/roles?workspace_id=${encodeURIComponent(workspace)}`, { signal }),
    configure: (workspace: string, roles: AgentRoles) => apiFetch<AgentRoles>(`${localBase}/agents/roles?workspace_id=${encodeURIComponent(workspace)}`, {
        method: 'PUT', body: JSON.stringify({ expectedRevision: roles.revision, audiovisual: roles.audiovisual, image: roles.image })
    }),
    tasks: (id: string) => apiFetch<AgentTask[]>(`${localBase}/documents/${encodeURIComponent(id)}/agent-tasks`),
    plan: (id: string, revision: number, instruction: string, key: string) => apiFetch<AgentTask>(`${localBase}/documents/${encodeURIComponent(id)}/agent-tasks`, post({ expectedRevision: revision, instruction, role: 'auto' }, key)),
    apply: (id: string, task: AgentTask) => apiFetch<LocalDocument>(`${localBase}/documents/${encodeURIComponent(id)}/agent-tasks/${encodeURIComponent(task.id)}/apply`, post({ expectedRevision: task.documentRevision })),
    commands: (id: string, revision: number, commands: LocalOperation[], key: string) => apiFetch<LocalDocument>(`${localBase}/documents/${encodeURIComponent(id)}/local-commands`, post({ expectedRevision: revision, commands }, key)),
    preview: (id: string, signal?: AbortSignal) => apiFetchBlob(`${localBase}/documents/${encodeURIComponent(id)}/local-preview`, signal),
    exportImage: (id: string, revision: number, key: string) => apiFetch<{
        downloadUrl: string;
    }>(`${localBase}/documents/${encodeURIComponent(id)}/local-image-export`, post({ expectedRevision: revision }, key)),
};
