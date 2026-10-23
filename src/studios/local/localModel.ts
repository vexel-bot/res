import type { LocalKey, LocalLayer, AgentTask } from './localApi';

/** A concurrent history read may have observed a task before planning finished. */
export function mergeAgentTasks(current: AgentTask[], incoming: AgentTask[]) {
    const terminal = (task: AgentTask) => ['succeeded', 'failed', 'cancelled'].includes(task.status);
    const rows = new Map(current.map(task => [task.id, task]));
    for (const task of incoming) {
        const previous = rows.get(task.id);
        if (previous && (terminal(previous) && !terminal(task)
            || (previous.appliedRevision || 0) > (task.appliedRevision || 0))) continue;
        rows.set(task.id, task);
    }
    return [...rows.values()].sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
}

export function localRecoveryMatchesProject(requestedId: string | null, recoveredId: string | undefined) {
    return !requestedId || requestedId === recoveredId;
}
export function localError(message: string) {
    const messages: Record<string,string> = {
        studio_document_conflict: 'O projeto mudou no servidor. Recarregue a versão salva para continuar.',
        agent_local_model_unavailable: 'O modelo local não está disponível. Confira se o Ollama e o modelo escolhido estão instalados.',
        agent_media_duration_use_timeline_editor: 'Ajuste a duração dos materiais e do áudio no editor canônico.',
        local_text_does_not_fit: 'O texto não cabe na caixa. Aumente a área ou reduza o tamanho da fonte.',
        agent_template_duration_between_3_and_120_seconds: 'O modelo local de motion aceita de 3 a 120 segundos.',
        local_layer_exceeds_duration: 'Uma camada ou animação ultrapassa a duração do projeto.',
        agent_workspace_busy_or_interrupted_task: 'Há uma tarefa em andamento ou interrompida. Confira o histórico antes de repetir.',
        agent_planning_failed: 'O plano recebido não pôde ser validado. Nenhuma edição foi aplicada.',
        agent_selection_scope_violation: 'O plano tentou alterar elementos fora da seleção. Nenhuma edição foi aplicada. Desmarque a seleção para uma operação global.',
        local_scene_metadata_invalid: 'Os dados das cenas são inválidos. A versão salva foi preservada.',
    };
    return messages[message] || message;
}
export function valueAt(keys: LocalKey[] = [], property: LocalKey['property'], fallback: number, frame: number) {
    const points = keys.filter(key => key.property === property).sort((a, b) => a.frame - b.frame);
    if (!points.length)
        return fallback;
    if (frame <= points[0].frame)
        return points[0].value;
    for (let index = 1; index < points.length; index++) {
        const a = points[index - 1], b = points[index];
        if (frame <= b.frame) {
            let p = (frame - a.frame) / (b.frame - a.frame);
            if (b.easing === 'ease-in-out')
                p = p * p * (3 - 2 * p);
            if (b.easing === 'ease-out')
                p = 1 - (1 - p) ** 3;
            return a.value + (b.value - a.value) * p;
        }
    }
    return points.at(-1)!.value;
}
export function newLayer(kind: LocalLayer['kind'], width: number, height: number, duration?: number): LocalLayer {
    return { id: crypto.randomUUID(), kind, name: kind === 'text' ? 'Texto' : kind === 'shape' ? 'Forma' : 'Imagem',
        x: width * .1, y: height * .25, width: width * .8, height: height * .4,
        opacity: 1, rotation: 0, visible: true, locked: false, zIndex: 10,
        properties: { schemaVersion: 'studio.local-layer.v1', ...(kind === 'text' ? { text: 'Seu texto', fontSize: Math.round(width / 20), color: '#FFFFFF' } : { fill: '#FF7F50', radius: 12 }),
            ...(duration ? { startFrame: 0, durationFrames: duration } : {}) } };
}

export function duplicateLayer(layer: LocalLayer, layers: LocalLayer[]): LocalLayer {
    if (layer.locked) throw new Error('Desbloqueie o elemento antes de duplicar.');
    if (layers.length >= 24) throw new Error('O projeto aceita até 24 camadas locais.');
    return { ...structuredClone(layer), id: crypto.randomUUID(), name: `${layer.name} · cópia`,
        x:layer.x+12, y:layer.y+12, zIndex:Math.max(...layers.map(row=>row.zIndex),0)+1 };
}

export function containsPoint(layer: LocalLayer, frame: number, x: number, y: number) {
    const t=frame-(layer.properties.startFrame || 0), keys=layer.properties.keyframes;
    const scale=valueAt(keys,'scale',1,t), angle=-valueAt(keys,'rotation',layer.rotation,t)*Math.PI/180;
    const dx=x-layer.x-layer.width/2-valueAt(keys,'x',0,t), dy=y-layer.y-layer.height/2-valueAt(keys,'y',0,t);
    const localX=(dx*Math.cos(angle)-dy*Math.sin(angle))/scale;
    const localY=(dx*Math.sin(angle)+dy*Math.cos(angle))/scale;
    return Math.abs(localX)<=layer.width/2 && Math.abs(localY)<=layer.height/2;
}

export function localScenes(narrative: unknown): {id:string;title:string;startFrame:number;durationFrames:number}[] {
    if (!narrative || typeof narrative !== 'object') return [];
    const production=(narrative as Record<string,unknown>).localProduction;
    if (!production || typeof production !== 'object') return [];
    const scenes=(production as Record<string,unknown>).scenes;
    if (!Array.isArray(scenes)) return [];
    const result:{id:string;title:string;startFrame:number;durationFrames:number}[]=[];
    for(const value of scenes.slice(0,24)) {
        if (!value || typeof value !== 'object') continue;
        const row=value as Record<string,unknown>;
        if (typeof row.id==='string' && typeof row.title==='string' && Number.isInteger(row.startFrame)
            && Number.isInteger(row.durationFrames) && Number(row.startFrame)>=0 && Number(row.durationFrames)>0
            && !result.some(scene=>scene.id===row.id)) result.push({id:row.id,title:row.title,
                startFrame:Number(row.startFrame),durationFrames:Number(row.durationFrames)});
    }
    return result;
}
