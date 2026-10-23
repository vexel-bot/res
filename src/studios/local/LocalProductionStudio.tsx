import React from 'react';
import { Download, Layers, Pause, Play, Plus, Save, Sparkles, Type, Upload, Undo2, Redo2 } from 'lucide-react';
import { apiFetch, apiFetchBlob, APIError } from '../../api';
import { productApi, type AssetRecord, type StudioGenerationJobRecord, type StudioDocumentVersionRecord } from '../../api/productApi';
import { useProductData } from '../../context/ProductDataContext';
import { useGovernance } from '../../context/GovernanceContext';
import { useOperations } from '../../context/OperationsContext';
import { klicPageScope, useKlicPageDetails } from '../../klic/pageContext';
import { LocalSelect as ClickoSelectMenu } from './LocalSelect';
import { craftApi, type CraftDocument, type LLMConnection } from '../craft/craftApi';
import { CanonicalVideoEditor } from '../video/CanonicalVideoEditor';
import { videoOutputUrl } from '../video/canonicalVideoApi';
import { LocalMonitor } from './LocalMonitor';
import { localApi, localBase, type LocalDocument, type LocalLayer, type LocalOperation, type AgentTask, type AgentRoles } from './localApi';
import { localError, newLayer, duplicateLayer, localScenes, localRecoveryMatchesProject, mergeAgentTasks } from './localModel';
import { LocalLayerControls } from './LocalLayerControls';
import './local-production.css';
import type { NavigationTab } from '../../types';
type Pending = {
    path: string;
    body: unknown;
    key: string;
};
export function LocalProductionStudio({ module, onNavigate }: {
    module: 'create-image' | 'create-video';
    onNavigate?: (tab: NavigationTab) => void;
}) {
    const data = useProductData();
    if (data.status === 'error') return <section className="lp-root lp-access-state" role="alert">
        <h2>Não foi possível abrir este Studio</h2><p>{data.error}</p>
        <p>Confira a conta e o cliente selecionados. Acesso, licença e isolamento continuam sendo verificados pelo servidor.</p>
        <div className="lp-actions"><button onClick={() => void data.refresh()}>Tentar novamente</button>
            {onNavigate && <button onClick={() => onNavigate('workspace')}>Ver clientes e ambiente</button>}</div>
    </section>;
    if (data.status !== 'ready' || !data.activeWorkspace || !data.bootstrap)
        return <p role="status">{data.error || 'Carregando ambiente de produção…'}</p>;
    return <LocalRoom key={`${data.bootstrap.user.id}:${data.activeWorkspace.id}:${module}`} module={module} workspaceId={data.activeWorkspace.id} userId={data.bootstrap.user.id}/>;
}
function LocalRoom({ module, workspaceId, userId }: {
    module: 'create-image' | 'create-video';
    workspaceId: string;
    userId: string;
}) {
    const data = useProductData();
    const { activeAccount } = useGovernance();
    const { activeClient } = useOperations();
    const video = module === 'create-video';
    const storageKey = `clicko:local-production:v1:${userId}:${workspaceId}:${module}`;
    const [doc, setDoc] = React.useState<LocalDocument>();
    const [projects, setProjects] = React.useState<LocalDocument[]>([]);
    const [extraAssets, setExtraAssets] = React.useState<AssetRecord[]>([]);
    const [selected, setSelected] = React.useState<string>();
    const [dirty, setDirty] = React.useState(false);
    const [undo, setUndo] = React.useState<LocalDocument['composition'][]>([]);
    const [redo, setRedo] = React.useState<LocalDocument['composition'][]>([]);
    const [instruction, setInstruction] = React.useState(video ? 'Crie um motion design de 12 segundos sobre inteligência artificial.' : 'Crie um cartão com o título "Ideias que ganham forma".');
    const [title, setTitle] = React.useState(video ? 'Meu motion design' : 'Minha composição');
    const [tasks, setTasks] = React.useState<AgentTask[]>([]);
    const [roles, setRoles] = React.useState<AgentRoles>();
    const [connections, setConnections] = React.useState<LLMConnection[]>([]);
    const [canConfigure, setCanConfigure] = React.useState(false);
    const [busy, setBusy] = React.useState(false);
    const [error, setError] = React.useState('');
    const [notice, setNotice] = React.useState('');
    const [job, setJob] = React.useState<StudioGenerationJobRecord>();
    const [versions, setVersions] = React.useState<StudioDocumentVersionRecord[]>([]);
    const [frame, setFrame] = React.useState(0);
    const [playing, setPlaying] = React.useState(false);
    const [download, setDownload] = React.useState<string>();
    const [mediaOpen, setMediaOpen] = React.useState(false);
    const [pending, setPending] = React.useState<Pending>();
    const pendingRef = React.useRef<Pending | undefined>(undefined);
    const inFlight = React.useRef(false);
    const file = React.useRef<HTMLInputElement>(null);
    const mounted = React.useRef(true);
    const modelField = React.useRef<HTMLInputElement>(null);
    const page = doc?.composition.pages[0];
    const layer = page?.layers.find(layer => layer.id === selected) as LocalLayer | undefined;
    const timeline = doc?.composition.mediaTimeline;
    const fps = timeline ? timeline.frameRate.numerator / timeline.frameRate.denominator : 24;
    const duration = timeline?.durationFrames || 1;
    const rendering = Boolean(job && !['succeeded', 'failed', 'cancelled'].includes(job.status));
    const locked = busy || Boolean(pending) || rendering || mediaOpen;
    useKlicPageDetails(module, klicPageScope(activeAccount.workspaceId, activeClient?.id), {
        view: video ? 'Motion Design Studio' : 'Image Studio local', ...(doc ? { selected: { kind: 'studio-document', id: doc.documentId },
            selectedLayerIds: selected && layer ? [selected] : [] } : {})
    });
    React.useEffect(() => {
        mounted.current = true;
        const requestedId = new URLSearchParams(window.location.search).get('document');
        let recoveredId: string | undefined;
        let rememberedId: string | undefined;
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey) || 'null') as {
                doc?: LocalDocument;
                pending?: Pending;
                selectedId?: string;
            } | null;
            const matches = localRecoveryMatchesProject(requestedId, saved?.doc?.documentId || saved?.selectedId);
            rememberedId = saved?.selectedId;
            if (!matches && saved && (saved.doc || saved.pending)) {
                localStorage.setItem(storageKey + ':previous', JSON.stringify(saved));
                setNotice('Abrindo o projeto solicitado. O rascunho anterior foi preservado como backup local.');
            }
            if (matches && saved?.doc?.workspaceId === workspaceId) {
                setDoc(saved.doc);
                setDirty(true);
                recoveredId = saved.doc.documentId;
                setNotice('Rascunho local recuperado. Confira e salve para continuar.');
            }
            if (matches && saved?.pending?.path?.startsWith(localBase + '/')) {
                pendingRef.current = saved.pending;
                setPending(saved.pending);
            }
        }
        catch {
            setError('A recuperação local não pôde ser lida. O projeto salvo continua no servidor.');
        }
        const controller = new AbortController();
        void localApi.list(workspaceId, controller.signal).then(rows => {
            if (controller.signal.aborted)
                return;
            const compatible = rows.filter(row => row.contentType === (video ? 'video' : 'visual') && !row.nativeEditorState && row.composition.pages.length === 1
                && row.composition.pages[0].layers.every(layer => layer.properties?.schemaVersion === 'studio.local-layer.v1'));
            setProjects(compatible);
            const id = requestedId || rememberedId;
            if (id && !recoveredId) {
                const target = compatible.find(row => row.documentId === id);
                if (target) {
                    setDoc(target);
                    setDirty(false);
                }
                else
                    setError('O projeto solicitado não está disponível neste ambiente.');
            }
        }).catch(e => { if (!controller.signal.aborted)
            setError(e.message); });
        void localApi.roles(workspaceId, controller.signal).then(value => { if (!controller.signal.aborted)
            setRoles(value); }).catch(e => { if (!controller.signal.aborted)
            setError(e.message); });
        void craftApi.llmConnections(workspaceId, controller.signal).then(value => { if (!controller.signal.aborted) {
            setConnections(value.connections);
            setCanConfigure(value.canManage);
        } }).catch(() => { });
        return () => { mounted.current = false; controller.abort(); };
    }, [workspaceId, storageKey, video]);
    React.useEffect(() => {
        if (doc)
            localStorage.setItem(storageKey, JSON.stringify({ selectedId: doc.documentId, doc: dirty || pending ? doc : undefined, pending }));
    }, [storageKey, doc, dirty, pending]);
    React.useEffect(() => {
        if (!doc)
            return;
        let active = true;
        void localApi.tasks(doc.documentId).then(value => { if (active)
            setTasks(rows => mergeAgentTasks(rows, value)); }).catch(e => { if (active)
            setError(e.message); });
        void productApi.studioDocumentVersions(doc.documentId).then(value => { if (active)
            setVersions(value); }).catch(e => { if (active)
            setError(e.message); });
        return () => { active = false; };
    }, [doc?.documentId, doc?.revision]);
    React.useEffect(() => {
        if (!dirty && !pending && !busy)
            return;
        const before = (event: Event) => { event.preventDefault(); setNotice('Salve ou confirme a operação antes de trocar de área.'); };
        const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
        window.addEventListener('clicko:studio-before-leave', before);
        window.addEventListener('beforeunload', unload);
        return () => { window.removeEventListener('clicko:studio-before-leave', before); window.removeEventListener('beforeunload', unload); };
    }, [dirty, pending, busy]);
    React.useEffect(() => {
        if (!playing || !timeline)
            return;
        let handle = 0, start = performance.now(), initial = frame;
        const tick = (now: number) => { setFrame((initial + Math.floor((now - start) * fps / 1000)) % duration); handle = requestAnimationFrame(tick); };
        handle = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(handle);
    }, [playing, fps, duration]);
    React.useEffect(() => {
        if (!rendering || !job)
            return;
        const timer = setTimeout(() => {
            void productApi.studioGenerationJob(job.id).then(value => {
                if (!mounted.current)
                    return;
                setJob(value);
                if (value.status === 'succeeded' && value.result?.assetId)
                    setDownload(videoOutputUrl(String(value.result.assetId), workspaceId, activeClient?.id));
            }).catch(e => { if (mounted.current)
                setError(e.message); });
        }, 1200);
        return () => clearTimeout(timer);
    }, [job, rendering, workspaceId, activeClient?.id]);
    function adopt(value: LocalDocument) {
        if (doc?.documentId !== value.documentId) {
            setTasks([]);
            setVersions([]);
            setSelected(undefined);
            setJob(undefined);
            setDownload(undefined);
            setMediaOpen(false);
            setPlaying(false);
        }
        else if (doc?.revision !== value.revision) {
            setDownload(undefined);
        }
        setDoc(value);
        setDirty(false);
        setUndo([]);
        setRedo([]);
        setFrame(value.composition.mediaTimeline ? Math.min(frame, value.composition.mediaTimeline.durationFrames - 1) : 0);
        setProjects(rows => [value, ...rows.filter(row => row.documentId !== value.documentId)]);
    }
    async function run(action: () => Promise<unknown>) { if (inFlight.current)
        return; inFlight.current = true; setBusy(true); setError(''); setNotice(''); try {
        await action();
    }
    catch (e) {
        if (mounted.current)
                setError(e instanceof Error ? localError(e.message) : 'Não foi possível concluir.');
    }
    finally {
        inFlight.current = false;
        if (mounted.current)
            setBusy(false);
    } }
    async function write<T>(path: string, body: unknown) {
        if (pendingRef.current)
            throw new Error('Confirme a operação pendente antes de iniciar outra.');
        const value = { path, body, key: crypto.randomUUID() };
        pendingRef.current = value;
        setPending(value);
        localStorage.setItem(storageKey, JSON.stringify({ doc, pending: value }));
        try {
            const result = await apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body), headers: { 'Idempotency-Key': value.key } });
            pendingRef.current = undefined;
            setPending(undefined);
            return result;
        }
        catch (e) {
            if (e instanceof APIError && [400, 401, 403, 404, 409, 422].includes(e.status)) {
                pendingRef.current = undefined;
                setPending(undefined);
            }
            throw e;
        }
    }
    async function confirmPending() {
        if (!pending) return;
        try {
            const result = await apiFetch<unknown>(pending.path, {
                method:'POST', body:JSON.stringify(pending.body), headers:{'Idempotency-Key':pending.key},
            });
            pendingRef.current=undefined; setPending(undefined);
            if (result && typeof result==='object' && 'documentId' in result && 'composition' in result) {
                adopt(await localApi.document(String(result.documentId)));
            } else if (result && typeof result==='object' && 'role' in result) {
                setTasks(rows=>[result as AgentTask,...rows.filter(row=>row.id!==(result as AgentTask).id)]);
            } else if (result && typeof result==='object' && 'jobType' in result) {
                const job=result as StudioGenerationJobRecord; setJob(job);
                if(job.status==='succeeded'&&job.result?.assetId)setDownload(videoOutputUrl(String(job.result.assetId),workspaceId,activeClient?.id));
            } else if (result && typeof result==='object' && 'downloadUrl' in result) {
                await downloadImage(String(result.downloadUrl));
            }
            setNotice('Operação confirmada.');
        } catch(error) {
            if(error instanceof APIError && [400,401,403,404,409,422].includes(error.status)) {
                pendingRef.current=undefined;setPending(undefined);
            }
            throw error;
        }
    }
    async function downloadImage(path:string) {
        const url=URL.createObjectURL(await apiFetchBlob(path));
        const link=document.createElement('a');link.href=url;link.download='clicko-composicao.png';link.click();
        setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
    function change(composition: LocalDocument['composition']) { if (!doc || locked)
        return; setUndo(items => [...items.slice(-29), doc.composition]); setRedo([]); setDoc({ ...doc, composition }); setDirty(true); setDownload(undefined); }
    function patch(update: Partial<LocalLayer>, properties?: Partial<LocalLayer['properties']>) { if (!page || !layer || layer.locked)
        return; change({ ...doc!.composition, pages: [{ ...page, layers: page.layers.map(item => item.id === layer.id ? { ...item, ...update, properties: { ...item.properties, ...properties } } : item) }] }); }
    async function save() { if (!doc)
        return; if (!dirty)
        return doc; const updated = await write<LocalDocument>(`${localBase}/documents/${doc.documentId}/local-commands`, { expectedRevision: doc.revision, commands: [{ id: 'composition.replace', params: { composition: doc.composition } }] }); adopt(updated); return updated; }
    async function plan() {
        let current = await save();
        if (!current) {
            current = await write<LocalDocument>(`${localBase}/agents/projects`, { workspaceId, title, contentType: video ? 'video' : 'visual', width: video ? 1280 : 1080, height: video ? 720 : 1080 });
            adopt(current);
        }
        const task = await write<AgentTask>(`${localBase}/documents/${current.documentId}/agent-tasks`, { expectedRevision: current.revision, instruction, role: 'auto',
            selectedLayerIds: selected && current.composition.pages[0].layers.some(row=>row.id===selected) ? [selected] : [] });
        setTasks(rows => [task, ...rows.filter(row => row.id !== task.id)]);
        if (task.status === 'failed')
            throw new Error(task.errorCode || 'O planejamento falhou.');
    }
    async function apply(task: AgentTask) { if (!doc)
        return; const value = await write<LocalDocument>(`${localBase}/documents/${doc.documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: task.documentRevision }); adopt(value); setNotice('Plano aplicado. Os elementos continuam editáveis.'); }
    async function upload(selectedFile: File) {
        if (!doc || !page)
            return;
        const current = await save();
        if (!current)
            return;
        if (selectedFile.size > 32 * 1024 * 1024)
            throw new Error('Importe materiais de até 32 MB neste painel.');
        const asset = await craftApi.uploadAsset(workspaceId, selectedFile);
        setExtraAssets(rows => [asset, ...rows.filter(row => row.id !== asset.id)]);
        await insertAsset(asset, current);
    }
    async function insertAsset(asset: AssetRecord, saved?: LocalDocument) {
        const current = saved || await save();
        if (!current) return;
        const page = current.composition.pages[0];
        const timeline = current.composition.mediaTimeline;
        const duration = timeline?.durationFrames || 1;
        const fps = timeline ? timeline.frameRate.numerator/timeline.frameRate.denominator : 24;
        if(asset.metadata?.rightsStatus === 'restricted') throw new Error('Este material possui restrição de uso.');
        const operations: LocalOperation[] = [{ id: 'asset.attach', params: { assetId: asset.id } }];
        if (asset.mediaType?.startsWith('image/')) {
            const graphic = newLayer('image', page.width, page.height, video ? duration : undefined);
            graphic.name = asset.title || 'Imagem da biblioteca';
            graphic.zIndex = page.layers.length + 20;
            graphic.properties.assetId = asset.id;
            operations.push({ id: 'layer.upsert', params: { layer: graphic } });
        }
        else if (video && /^(audio|video)\//.test(asset.mediaType || '')) {
            const info = await apiFetch<{
                durationSeconds: number;
            }>(`${localBase}/video/assets/${asset.id}/probe?workspace_id=${encodeURIComponent(workspaceId)}`);
            const timeline = structuredClone(current.composition.mediaTimeline!);
            const kind = asset.mediaType?.startsWith('audio/') ? 'audio' : 'video';
            timeline.tracks.push({ id: crypto.randomUUID(), kind, name: asset.title || 'Material da biblioteca', clips: [{ id: crypto.randomUUID(), assetId: asset.id, timeline: { startFrame: 0, durationFrames: Math.min(duration, Math.floor(info.durationSeconds * fps)) }, ...(kind === 'audio' ? { gainDb: -6 } : { transform: { originalAudioEnabled: true } }) }] });
            operations.push({ id: 'timeline.replace', params: { timeline } });
        }
        else
            throw new Error('Este formato não pode ser inserido no projeto atual.');
        adopt(await write<LocalDocument>(`${localBase}/documents/${current.documentId}/local-commands`, { expectedRevision: current.revision, commands: operations }));
    }
    async function exportProject() {
        const current = await save();
        if (!current)
            return;
        if (video) {
            setJob(await write<StudioGenerationJobRecord>(`${localBase}/video/documents/${current.documentId}/render-jobs`, { expectedRevision: current.revision }));
        }
        else {
            const result = await write<{
                downloadUrl: string;
            }>(`${localBase}/documents/${current.documentId}/local-image-export`, { expectedRevision: current.revision });
            await downloadImage(result.downloadUrl);
            setNotice('PNG exportado; o projeto e os originais foram preservados.');
        }
    }
    const options = projects.map(row => ({ value: row.documentId, label: row.title }));
    const usableConnections = connections.filter(row => row.config.enabled && row.config.billingMode === 'local_free' && row.config.protocol === 'ollama_chat' && !row.hasCredential);
    const materials = [...extraAssets,...(data.snapshot?.assets || [])].filter((asset,index,rows)=>
        rows.findIndex(row=>row.id===asset.id)===index && /^(image|video|audio)\//.test(asset.mediaType || '')
        && (video || asset.mediaType?.startsWith('image/')));
    const scenes = localScenes(doc?.composition.narrative);
    return <section className="lp-root vs-root" aria-label={video ? 'Motion Design Studio local' : 'Image Studio local'}>
    <header className="lp-header"><div><small>PRODUÇÃO LOCAL · CUSTO EXTERNO R$ 0</small><h2>{video ? 'Motion Design Studio' : 'Image Studio'}</h2><p>Crie, ajuste e exporte um projeto com elementos editáveis.</p></div><button onClick={() => window.dispatchEvent(new Event('clicko:klic-production-open'))}><Sparkles size={16}/>KLIC</button></header>
    {error && <p role="alert" className="lp-error">{error}</p>}{notice && <p role="status">{notice}</p>}
    {doc && dirty && !pending && <button disabled={busy} onClick={()=>void run(async()=>{localStorage.setItem(storageKey+':previous',JSON.stringify(doc));adopt(await localApi.document(doc.documentId));setNotice('Versão salva recarregada. O rascunho anterior foi guardado como backup local.');})}>Recarregar versão salva</button>}
    {pending && <aside className="lp-recovery"><p>Uma operação aguarda confirmação. Repetir utiliza a mesma identificação.</p><button disabled={busy} onClick={() => void run(confirmPending)}>Confirmar operação pendente</button></aside>}
    {selected && <div className="lp-actions"><span>Alvo dos comandos: {layer?.name || 'camada selecionada'}</span><button disabled={locked} onClick={()=>setSelected(undefined)}>Desmarcar · editar projeto inteiro</button></div>}
    {doc && <section className="lp-materials"><h3>Biblioteca compartilhada · materiais deste ambiente</h3><p>Reutilize imagens, composições PNG, vídeos e áudio sem alterar o original. Os direitos e o escopo são verificados no servidor.</p><div className="lp-actions">{materials.length ? materials.map(asset=><button key={asset.id} disabled={locked} onClick={()=>void run(()=>insertAsset(asset))}>{asset.title || asset.id} · {asset.mediaType}</button>) : <p>Importe um material próprio para começar.</p>}</div></section>}
    {scenes.length > 0 && <nav className="lp-scenes" aria-label="Cenas do motion">{scenes.map((scene,index)=><button key={scene.id} onClick={()=>{setPlaying(false);setFrame(scene.startFrame);setSelected(undefined);}}>Cena {index+1} · {scene.title}</button>)}</nav>}
    {tasks.length > 0 && <details className="lp-task-history"><summary>Histórico dos agentes · {tasks.length} tarefas</summary>{tasks.map(task=><article key={task.id}><strong>{task.role} · {task.status}{task.appliedRevision ? ` · aplicado na revisão ${task.appliedRevision}` : ''}</strong><p>{task.instruction}</p><small>{task.id} · {task.provider} · custo externo R$ 0</small>{task.history?.map((event,index)=><p key={index}>{event.type} · {event.at}</p>)}</article>)}</details>}
    <div className="lp-toolbar"><div className="lp-project-picker"><ClickoSelectMenu value={doc?.documentId || ''} options={[{ value: '', label: 'Selecionar projeto' }, ...options]} onChange={id => { if (!locked && !dirty) {
        const found = projects.find(row => row.documentId === id);
        if (found)
            adopt(found);
    } }} ariaLabel="Projeto local" disabled={locked || dirty}/></div><button disabled={locked || dirty} onClick={() => { setDoc(undefined); setTasks([]); setSelected(undefined); setDownload(undefined); setJob(undefined); }}>Novo projeto</button>{doc && <><button disabled={locked || !dirty} onClick={() => void run(save)}><Save size={15}/>Salvar</button><button disabled={locked} onClick={() => void run(exportProject)}><Download size={15}/>Exportar {video ? 'MP4' : 'PNG'}</button><span>v{doc.version} · revisão {doc.revision}{dirty ? ' · alterações locais' : ''}</span></>}</div>
    <section className="lp-brief"><label>{doc ? 'Comando para o projeto' : 'Nome do projeto'}{!doc && <input value={title} maxLength={120} onChange={event => setTitle(event.target.value)}/>}</label><textarea aria-label="Briefing ou comando de produção" value={instruction} maxLength={8000} onChange={event => setInstruction(event.target.value)} rows={3}/><button disabled={locked || !instruction.trim() || (!doc && !title.trim())} onClick={() => void run(plan)}><Sparkles size={15}/>{busy ? 'Processando…' : 'Preparar plano'}</button><p>{roles?.[video ? 'audiovisual' : 'image'].mode === 'local_model' ? 'Modelo local configurado; a aplicação do plano continua sujeita à validação.' : 'Regras locais: criar motion/cartão, alterar o primeiro título entre aspas, cores em #hex e duração. Não há inferência de IA neste modo.'}</p></section>
    {tasks[0] && <section className="lp-plan" aria-label="Plano do agente"><strong>{tasks[0].role === 'image' ? 'Agente visual' : 'Agente audiovisual'}</strong><p>{tasks[0].result?.rationale || tasks[0].errorCode}</p><small>{tasks[0].provider} · {tasks[0].result?.commands?.length || 0} operações · {tasks[0].result?.state}</small><button disabled={locked || dirty || !tasks[0].result?.commands?.length || tasks[0].status !== 'succeeded' || tasks[0].documentRevision !== doc?.revision} onClick={() => void run(() => apply(tasks[0]))}>Aplicar plano</button></section>}
    {doc && page && <><div className="lp-grid"><aside className="lp-layers"><h3>Camadas</h3><div className="lp-actions"><button disabled={locked} onClick={() => { const layer = newLayer('text', page.width, page.height, video ? duration : undefined); change({ ...doc.composition, pages: [{ ...page, layers: [...page.layers, layer] }] }); setSelected(layer.id); }}><Type size={15}/>Texto</button><button disabled={locked} onClick={() => { const layer = newLayer('shape', page.width, page.height, video ? duration : undefined); change({ ...doc.composition, pages: [{ ...page, layers: [...page.layers, layer] }] }); setSelected(layer.id); }}><Plus size={15}/>Forma</button><button disabled={locked} onClick={() => file.current?.click()}><Upload size={15}/>Importar</button></div><input ref={file} type="file" hidden accept={video ? 'image/png,image/jpeg,image/webp,video/mp4,audio/wav,audio/mpeg' : 'image/png,image/jpeg,image/webp'} onChange={event => { const chosen = event.target.files?.[0]; event.target.value = ''; if (chosen)
            void run(() => upload(chosen)); }}/>{[...page.layers].sort((a, b) => b.zIndex - a.zIndex).map(row => <button key={row.id} className={selected === row.id ? 'is-active' : ''} onClick={() => setSelected(row.id)}><Layers size={14}/><span>{row.name}</span>{row.locked && <small>Bloqueada</small>}</button>)}<div className="lp-actions"><button aria-label="Desfazer edição local" disabled={locked || !undo.length} onClick={() => { const previous = undo.at(-1)!; setRedo(items => [doc.composition, ...items]); setUndo(items => items.slice(0, -1)); setDoc({ ...doc, composition: previous }); setDirty(true); }}><Undo2 size={15}/></button><button aria-label="Refazer edição local" disabled={locked || !redo.length} onClick={() => { setUndo(items => [...items, doc.composition]); setDoc({ ...doc, composition: redo[0] }); setRedo(items => items.slice(1)); setDirty(true); }}><Redo2 size={15}/></button></div></aside>
      <main className="lp-view"><LocalMonitor doc={doc} frame={frame} selected={selected} onSelect={setSelected}/>{video && <div className="lp-playback"><button aria-label={playing ? 'Pausar prévia' : 'Reproduzir prévia'} onClick={() => setPlaying(value => !value)}>{playing ? <Pause size={16}/> : <Play size={16}/>}</button><input type="range" aria-label="Posição na timeline" min={0} max={duration - 1} value={frame} onChange={event => { setPlaying(false); setFrame(Number(event.target.value)); }}/><span>{(frame / fps).toFixed(1)} / {(duration / fps).toFixed(1)} s</span></div>}{timeline?.tracks.some(track => (track.clips?.length || track.cues?.length)) && <p>Os materiais e o áudio aparecem juntos na exportação canônica abaixo.</p>}</main>
      <aside className="lp-properties"><h3>Propriedades</h3>{layer ? <fieldset disabled={locked || layer.locked}><label>Nome<input value={layer.name} onChange={event => patch({ name: event.target.value })}/></label>{layer.kind === 'text' && <><label>Texto<textarea value={layer.properties.text || ''} onChange={event => patch({}, { text: event.target.value })}/></label><label>Tamanho da fonte<input type="number" min={8} max={240} value={layer.properties.fontSize || 48} onChange={event => patch({}, { fontSize: Number(event.target.value) })}/></label><label>Cor<input type="color" value={layer.properties.color || '#FFFFFF'} onChange={event => patch({}, { color: event.target.value })}/></label></>}{layer.kind === 'shape' && <><label>Preenchimento<input type="color" value={layer.properties.fill || '#FF7F50'} onChange={event => patch({}, { fill: event.target.value })}/></label><label>Forma<ClickoSelectMenu value={layer.properties.shape || 'rectangle'} options={[{ value: 'rectangle', label: 'Retângulo' }, { value: 'ellipse', label: 'Elipse' }]} onChange={shape => patch({}, { shape: shape as 'rectangle' | 'ellipse' })} ariaLabel="Forma" disabled={locked}/></label><label>Cantos<input type="number" min={0} max={240} value={layer.properties.radius || 0} onChange={event => patch({}, { radius: Number(event.target.value) })}/></label></>}{(['x', 'y', 'width', 'height', 'rotation', 'opacity', 'zIndex'] as const).map(property => <label key={property}>{({ x: 'Posição X', y: 'Posição Y', width: 'Largura', height: 'Altura', rotation: 'Rotação', opacity: 'Opacidade', zIndex: 'Ordem' })[property]}<input type="number" step={property === 'opacity' ? 0.05 : 1} min={property === 'opacity' ? 0 : property === 'width' || property === 'height' ? 1 : undefined} max={property === 'opacity' ? 1 : undefined} value={layer[property]} onChange={event => patch({ [property]: Number(event.target.value) })}/></label>)}{layer.kind === 'image' && <>{(['brightness', 'contrast', 'saturation'] as const).map(property => <label key={property}>{({ brightness: 'Brilho', contrast: 'Contraste', saturation: 'Saturação' })[property]}<input type="range" min={property === 'saturation' ? 0 : 0.25} max={2} step={.05} value={layer.properties[property] ?? 1} onChange={event => patch({}, { [property]: Number(event.target.value) })}/></label>)}<button onClick={() => patch({}, { crop: { x: .1, y: .1, width: .8, height: .8 } })}>Recortar 10% nas bordas</button><button onClick={() => patch({}, { crop: null })}>Restaurar recorte original</button></>}{video && <><label>Início (quadros)<input type="number" min={0} max={duration - 1} value={layer.properties.startFrame || 0} onChange={event => patch({}, { startFrame: Number(event.target.value) })}/></label><label>Duração (quadros)<input type="number" min={1} max={duration} value={layer.properties.durationFrames || duration} onChange={event => patch({}, { durationFrames: Number(event.target.value) })}/></label><button onClick={() => patch({}, { keyframes: [{ property: 'x', frame: 0, value: -50 }, { property: 'x', frame: Math.min(24, layer.properties.durationFrames || duration), value: 0, easing: 'ease-out' }] })}>Animar entrada pela esquerda</button><details><summary>Keyframes</summary>{(layer.properties.keyframes || []).map((key, index) => <label key={index}>{key.property} · quadro {key.frame}<input type="number" value={key.value} step={.05} onChange={event => patch({}, { keyframes: layer.properties.keyframes!.map((item, i) => i === index ? { ...item, value: Number(event.target.value) } : item) })}/></label>)}</details></>}<button onClick={() => change({ ...doc.composition, pages: [{ ...page, layers: page.layers.filter(item => item.id !== layer.id) }] })}>Remover elemento</button></fieldset> : <p>Selecione uma camada para editar.</p>}<label>Fundo do projeto<input disabled={locked} type="color" value={page.background.slice(0, 7)} onChange={event => change({ ...doc.composition, pages: [{ ...page, background: event.target.value }] })}/></label></aside></div>
      {video && <section className="lp-timeline"><h3>Timeline editável</h3>{page.layers.map(layer => <div key={layer.id}><button onClick={() => setSelected(layer.id)}>{layer.name}</button><div><button aria-label={`Selecionar ${layer.name} na timeline`} style={{ marginLeft: `${(layer.properties.startFrame || 0) / duration * 100}%`, width: `${(layer.properties.durationFrames || duration) / duration * 100}%` }} onClick={() => setSelected(layer.id)}>{((layer.properties.durationFrames || duration) / fps).toFixed(1)} s</button></div></div>)}</section>}
      {layer && <details className="lp-animation-settings"><summary>Tipografia, acabamento e keyframes · {layer.name}</summary><LocalLayerControls layer={layer} disabled={locked} video={video} duration={duration} patch={patch} duplicate={()=>{
        try { const copy=duplicateLayer(layer,page.layers);change({...doc.composition,pages:[{...page,layers:[...page.layers,copy]}]});setSelected(copy.id); }
        catch(error) {setError(error instanceof Error ? error.message : 'Não foi possível duplicar.');}
      }}/></details>}
      {rendering && <p role="status">Renderizando… {job?.progress}% <button onClick={() => void run(async () => { setJob(await apiFetch(`${localBase}/jobs/${job!.id}/cancel`, { method: 'POST', body: JSON.stringify({ reason: 'Cancelado pelo usuário' }) })); })}>Cancelar</button></p>}{job?.status === 'failed' && <p role="alert">{job.errorMessage || job.errorCode}</p>}{download && <section className="lp-output"><h3>Exportação MP4</h3><video controls src={download}/><a href={download + (download.includes('?') ? '&' : '?') + 'download=1'} download>Baixar MP4</a></section>}
      {video && <section className="lp-advanced"><button disabled={busy || Boolean(pending) || dirty || rendering} onClick={() => { if (window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable: true })))
            setMediaOpen(value => !value); }}>{mediaOpen ? 'Voltar à composição' : 'Cortes, materiais e áudio · abrir editor canônico'}</button>{mediaOpen && <CanonicalVideoEditor key={doc.documentId} doc={doc as unknown as CraftDocument} assets={[...extraAssets,...(data.snapshot?.assets || [])].filter((asset,index,rows)=>rows.findIndex(item=>item.id===asset.id)===index)} visible onDocument={value => adopt(value as unknown as LocalDocument)} onUpload={() => file.current?.click()} onLibrary={() => file.current?.click()} userId={userId}/>}</section>}
      <details><summary>Histórico do projeto · {versions.length} versões</summary>{versions.map(version => <div className="lp-version" key={version.number}><span>v{version.number} · {version.label}</span><button disabled={locked || dirty} onClick={() => void run(async () => adopt(await productApi.restoreStudioDocumentVersion(doc.documentId, version.number, doc.revision) as LocalDocument))}>Restaurar</button></div>)}</details></>}
    <details className="lp-settings"><summary>Modelos dos agentes</summary><p>A KLIC mantém sua configuração Gemini. Cada especialista pode usar regras locais ou uma conexão Ollama já instalada. Nenhum modelo é baixado por este painel.</p>{roles && (['audiovisual', 'image'] as const).map(role => <label key={role}>{role === 'audiovisual' ? 'Audiovisual' : 'Imagem'}<ClickoSelectMenu ariaLabel={`Modelo do agente ${role}`} disabled={busy || !canConfigure} value={roles[role].mode === 'local_model' ? `${roles[role].connectionId}|${roles[role].model}` : 'local_tools'} options={[{ value: 'local_tools', label: 'Ferramentas locais · sem inferência' }, ...usableConnections.flatMap(connection => connection.config.models.filter(model => !model.toLowerCase().includes('cloud')).map(model => ({ value: `${connection.id}|${model}`, label: `${connection.label} · ${model}` })))]} onChange={value => { const [connectionId, model] = value.split('|'); setRoles({ ...roles, [role]: value === 'local_tools' ? { mode: 'local_tools' } : { mode: 'local_model', connectionId, model } }); }}/></label>)}<button disabled={busy || !roles || !canConfigure} onClick={() => void run(async () => { setRoles(await localApi.configure(workspaceId, roles!)); setNotice('Configuração dos agentes salva.'); })}>Salvar configuração</button><details><summary>Registrar Ollama local existente</summary><label>ID do modelo instalado<input ref={modelField} placeholder="qwen3:0.6b"/></label><button disabled={busy || !canConfigure} onClick={() => void run(async () => { const model = modelField.current?.value.trim(); if (!model)
        throw new Error('Informe o ID exato de um modelo já instalado.'); const connection = await craftApi.saveLLMConnection(workspaceId, { label: 'Ollama local', provider: 'ollama', protocol: 'ollama_chat', baseUrl: 'http://127.0.0.1:11434', models: [model], authHeader: 'Authorization', authPrefix: 'Bearer', enabled: true, billingMode: 'local_free', budgetUsd: 0, inputUsdPerMillion: 0, outputUsdPerMillion: 0, maxOutputTokens: 3000 }); setConnections(rows => [...rows, connection]); setNotice('Conexão registrada. A disponibilidade será verificada antes da inferência.'); })}>Registrar conexão</button></details></details>
  </section>;
}
