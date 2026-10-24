import React from 'react';
import { Download, FolderOpen, History, Layers, Pause, Play, Plus, Save, Sparkles, Type, Upload, Undo2, Redo2, Settings2 } from 'lucide-react';
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
import { LocalInspector } from './LocalInspector';
import { StudioEditorFrame, StudioKlicButton, StudioUtilityPanel, useStudioShortcuts } from '../shared/StudioWorkspace';
import type { StudioPane } from '../shared/studioWorkspaceModel';
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
    const [instruction, setInstruction] = React.useState('');
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
    const [utility, setUtility] = React.useState<'projects' | 'history' | 'project' | 'production' | 'output' | null>(null);
    const [pane, setPane] = React.useState<StudioPane>('preview');
    const [leftTab, setLeftTab] = React.useState<'layers' | 'materials'>('layers');
    const [format, setFormat] = React.useState(video ? '16:9' : '1:1');
    const editorRoot = React.useRef<HTMLElement>(null);
    useStudioShortcuts(editorRoot, !mediaOpen);
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
        view: mediaOpen ? 'Montagem audiovisual' : video ? 'Motion Design Studio' : 'Image Studio local', ...(doc ? { selected: { kind: 'studio-document', id: doc.documentId },
            selectedLayerIds: !mediaOpen && selected && layer ? [selected] : [] } : {})
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
            current = await createEmptyProject();
        }
        const task = await write<AgentTask>(`${localBase}/documents/${current.documentId}/agent-tasks`, { expectedRevision: current.revision, instruction, role: 'auto',
            selectedLayerIds: selected && current.composition.pages[0].layers.some(row=>row.id===selected) ? [selected] : [] });
        setTasks(rows => [task, ...rows.filter(row => row.id !== task.id)]);
        setUtility('production');
        if (task.status === 'failed')
            throw new Error(task.errorCode || 'O planejamento falhou.');
    }
    async function apply(task: AgentTask) { if (!doc)
        return; const value = await write<LocalDocument>(`${localBase}/documents/${doc.documentId}/agent-tasks/${task.id}/apply`, { expectedRevision: task.documentRevision }); adopt(value); setNotice('Plano aplicado. Os elementos continuam editáveis.'); }
    async function createEmptyProject() {
        const [width, height] = format === '1:1' ? [1080, 1080] : format === '9:16' ? [720, 1280] : [1280, 720];
        const current = await write<LocalDocument>(`${localBase}/agents/projects`, { workspaceId, title: title.trim() || (video ? 'Meu motion design' : 'Minha composição'), contentType: video ? 'video' : 'visual', width, height });
        adopt(current); setPane('preview'); return current;
    }
    async function upload(selectedFile: File, saved?: LocalDocument) {
        const current = saved || await save();
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
            setUtility('output');
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
    function selectLayer(id: string) { setSelected(id); setPane('properties'); }
    function undoLocal() {
        if (!doc || locked || !undo.length) return;
        setRedo(items => [doc.composition, ...items]); setDoc({ ...doc, composition: undo.at(-1)! }); setUndo(items => items.slice(0, -1)); setDirty(true); setDownload(undefined);
    }
    function redoLocal() {
        if (!doc || locked || !redo.length) return;
        setUndo(items => [...items, doc.composition]); setDoc({ ...doc, composition: redo[0] }); setRedo(items => items.slice(1)); setDirty(true); setDownload(undefined);
    }
    function addElement(kind: 'text' | 'shape') {
        if (!doc || !page || locked) return;
        const item = newLayer(kind, page.width, page.height, video ? duration : undefined);
        change({ ...doc.composition, pages: [{ ...page, layers: [...page.layers, item] }] }); selectLayer(item.id);
    }
    const projectButtons = <>
        <button type="button" onClick={() => setUtility('projects')}><FolderOpen size={15}/>Projetos</button>
        {doc && <button type="button" onClick={() => setUtility('history')} aria-label="Histórico do projeto"><History size={15}/></button>}
        <button type="button" onClick={() => setUtility('project')} aria-label="Configurações do projeto"><Settings2 size={15}/></button>
        <StudioKlicButton/>
    </>;
    const planningForm = <>
        <label>{doc ? 'Pedido de edição' : 'Descreva sua ideia'}<textarea className="studio-start__idea" aria-label="Briefing ou comando de produção" value={instruction} maxLength={8000} onChange={event => setInstruction(event.target.value)} rows={3} placeholder={video ? 'Ex.: três cenas sobre inovação, com títulos e cartões animados.' : 'Ex.: um cartão com o título “Ideias que ganham forma”.'}/></label>
        <button type="button" disabled={locked || !instruction.trim()} onClick={() => void run(plan)}><Sparkles size={15}/>{busy ? 'Preparando…' : 'Preparar plano'}</button>
        <p className="studio-compact-note">{roles?.[video ? 'audiovisual' : 'image'].mode === 'local_model' ? 'Modelo local configurado. Revise o plano antes de aplicar.' : 'Produção por regras locais, sem inferência de IA. Você também pode editar manualmente.'}</p>
    </>;
    const library = <div className="lp-material-list">
        <button type="button" disabled={locked} onClick={() => file.current?.click()}><Upload size={15}/>Importar arquivo</button>
        {materials.map(asset => <button type="button" key={asset.id} disabled={locked} onClick={() => void run(() => insertAsset(asset))}><span>{asset.title || 'Material sem título'}</span><small>{asset.mediaType?.split('/')[0] === 'audio' ? 'Áudio' : asset.mediaType?.startsWith('video/') ? 'Vídeo' : 'Imagem'}</small></button>)}
        {!materials.length && <p>Importe seus materiais para reutilizá-los aqui.</p>}
    </div>;
    return <section ref={editorRoot} className="lp-root vs-root lp-integrated" aria-label={video ? 'Motion Design Studio local' : 'Image Studio local'}>
        {error && <p role="alert" className="lp-error">{error}</p>}{notice && <p role="status" className="lp-notice">{notice}</p>}
        {pending && <aside className="lp-recovery"><p>Uma operação aguarda confirmação.</p><button disabled={busy} onClick={() => void run(confirmPending)}>Confirmar operação pendente</button></aside>}
        <input ref={file} type="file" hidden accept={video ? 'image/png,image/jpeg,image/webp,video/mp4,audio/wav,audio/mpeg' : 'image/png,image/jpeg,image/webp'} onChange={event => {
            const chosen = event.target.files?.[0]; event.target.value = '';
            if (chosen && !busy && !pending && !rendering) void run(async () => { const current = doc ? await save() : await createEmptyProject(); if (current) await upload(chosen, current); });
        }}/>
        {!doc && <div className="studio-start">
            <h2>{video ? 'O que vamos colocar em movimento?' : 'O que você quer criar?'}</h2>
            <p>Descreva uma ideia para revisar um plano, ou deixe em branco para editar manualmente.</p>
            <label>Descreva sua ideia <small>Opcional</small><textarea className="studio-start__idea" aria-label="Ideia inicial do projeto" value={instruction} maxLength={8000} rows={3} onChange={event => setInstruction(event.target.value)} placeholder={video ? "Ex.: três cenas sobre inovação, com títulos animados." : "Ex.: um cartão com o título “Ideias que ganham forma”."}/></label>
            <div className="studio-start__actions"><button type="button" className="lp-primary" disabled={locked} onClick={() => void run(instruction.trim() ? plan : createEmptyProject)}><Plus size={16}/>Criar projeto</button><button type="button" disabled={locked} onClick={() => file.current?.click()}><Upload size={15}/>Importar materiais</button>{projectButtons}</div>
            <details className="studio-fold"><summary>Nome e formato · opções</summary>
                <label>Nome do projeto<input value={title} maxLength={120} onChange={event => setTitle(event.target.value)}/></label>
                <label>Formato<ClickoSelectMenu value={format} options={[{ value:'1:1',label:'Quadrado · 1:1' },{ value:'16:9',label:'Horizontal · 16:9' },{ value:'9:16',label:'Vertical · 9:16' }]} onChange={setFormat} ariaLabel="Formato do projeto local" disabled={locked}/></label>
                {video && <p>Composição inicial de 12 s, a 24 fps. Duração e animações continuam editáveis.</p>}
            </details>
        </div>}
        {doc && page && !mediaOpen && <StudioEditorFrame pane={pane} onPaneChange={setPane}
            toolbar={<>
                <strong className="studio-project-title" title={doc.title}>{doc.title}</strong>
                <button type="button" data-studio-action="undo" aria-label="Desfazer edição local" title="Desfazer · Ctrl+Z" disabled={locked || !undo.length} onClick={undoLocal}><Undo2 size={15}/></button>
                <button type="button" data-studio-action="redo" aria-label="Refazer edição local" title="Refazer · Ctrl+Shift+Z" disabled={locked || !redo.length} onClick={redoLocal}><Redo2 size={15}/></button>
                <button type="button" data-studio-action="save" disabled={locked || !dirty} onClick={() => void run(save)}><Save size={15}/>Salvar</button>
                {video && <button type="button" aria-label={playing ? 'Pausar prévia' : 'Reproduzir prévia'} title={playing ? 'Pausar prévia' : 'Reproduzir prévia'} onClick={() => setPlaying(value => !value)}>{playing ? <Pause size={15}/> : <Play size={15}/>}</button>}
                <button type="button" className="lp-primary" disabled={locked} onClick={() => void run(exportProject)}><Download size={15}/>Exportar {video ? 'MP4' : 'PNG'}</button>
                <button type="button" onClick={() => setUtility('production')}>Produção{tasks[0]?.result?.commands?.length && !tasks[0]?.appliedRevision ? ' · plano' : ''}</button>
                {projectButtons}
                <span className="studio-save-state">{dirty ? 'Alterações não salvas' : 'Salvo'} · v{doc.version}{rendering ? ' · renderizando' : ''}</span>
            </>}
            materials={<>
                <nav className="studio-region-tabs" aria-label="Conteúdo lateral"><button type="button" aria-pressed={leftTab === 'layers'} onClick={() => setLeftTab('layers')}>Camadas</button><button type="button" aria-pressed={leftTab === 'materials'} onClick={() => setLeftTab('materials')}>Materiais</button></nav>
                {leftTab === 'materials' ? library : <div className="lp-layer-list">
                    <div className="lp-actions"><button type="button" disabled={locked} onClick={() => addElement('text')}><Type size={15}/>Texto</button><button type="button" disabled={locked} onClick={() => addElement('shape')}><Plus size={15}/>Forma</button><button type="button" disabled={locked} onClick={() => file.current?.click()} aria-label="Importar material"><Upload size={15}/></button></div>
                    {[...page.layers].sort((a,b) => b.zIndex - a.zIndex).map(row => <button type="button" key={row.id} className={selected === row.id ? 'is-active' : ''} onClick={() => selectLayer(row.id)}><Layers size={14}/><span>{row.name}</span>{row.locked && <small>Bloqueada</small>}</button>)}
                    {!page.layers.length && <p>Adicione texto, formas ou materiais. Selecione um elemento para editar suas propriedades.</p>}
                </div>}
                {video && <details className="studio-fold"><summary>Vídeo e áudio</summary><p>Cortes e mixagem usam a mesma composição salva.</p><button type="button" disabled={locked || dirty} onClick={() => {
                    if (window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable:true }))) setMediaOpen(true);
                }}>Editar cortes, materiais e áudio</button></details>}
            </>}
            preview={<>
                <div className="lp-canvas-stage" onDragOver={event => { if (!locked && event.dataTransfer.types.includes('Files')) event.preventDefault(); }} onDrop={event => {
                    if (!event.dataTransfer.files.length) return; event.preventDefault();
                    if (event.dataTransfer.files.length > 1) { setError('Importe um arquivo por vez para confirmar cada material no projeto.'); return; }
                    const picked = event.dataTransfer.files[0];
                    if (!locked) void run(() => upload(picked));
                }}><LocalMonitor doc={doc} frame={frame} selected={selected} onSelect={selectLayer}/></div>
                {video && <div className="lp-playback"><input type="range" aria-label="Posição na timeline" min={0} max={duration-1} value={frame} onChange={event => {setPlaying(false);setFrame(Number(event.target.value));}}/><span>{(frame/fps).toFixed(1)} / {(duration/fps).toFixed(1)} s</span></div>}
                {timeline?.tracks.some(track => track.clips?.length || track.cues?.length) && <p className="studio-compact-note">Prévia de camadas. Confira vídeo e áudio juntos na exportação ou em “Vídeo e áudio”.</p>}
                {download && <button type="button" onClick={() => setUtility('output')}>Visualizar MP4 exportado</button>}
            </>}
            inspector={layer ? <LocalInspector layer={layer} locked={locked} video={video} duration={duration} patch={patch} deselect={() => {setSelected(undefined);setPane('preview');}} duplicate={() => {
                try { const copy=duplicateLayer(layer,page.layers);change({...doc.composition,pages:[{...page,layers:[...page.layers,copy]}]});selectLayer(copy.id); }
                catch(e) {setError(e instanceof Error ? e.message : 'Não foi possível duplicar.');}
            }} remove={() => {change({...doc.composition,pages:[{...page,layers:page.layers.filter(item => item.id !== layer.id)}]});setSelected(undefined);setPane('preview');}}/> : undefined}
            timeline={video ? <section className="lp-integrated-timeline" aria-label="Timeline editável">
                <header><h3>Timeline</h3><small>{(duration/fps).toFixed(1)} s · {fps} fps</small></header>
                {scenes.length > 0 && <nav className="lp-scenes" aria-label="Cenas do motion">{scenes.map((scene,index) => <button type="button" title={scene.title} key={scene.id} onClick={() => {setPlaying(false);setFrame(scene.startFrame);setSelected(undefined);}}>Cena {index+1}</button>)}</nav>}
                {page.layers.map(row => <div className="lp-time-row" key={row.id}><button type="button" onClick={() => selectLayer(row.id)}>{row.name}</button><div><button type="button" aria-label={'Selecionar '+row.name+' na timeline'} className={selected===row.id?'is-active':''} style={{left:((row.properties.startFrame||0)/duration*100)+'%',width:Math.min((row.properties.durationFrames||duration),duration-(row.properties.startFrame||0))/duration*100+'%'}} onClick={() => selectLayer(row.id)}>{((row.properties.durationFrames||duration)/fps).toFixed(1)} s</button></div></div>)}
                {!page.layers.length && <p>As camadas adicionadas aparecem aqui.</p>}
            </section> : undefined}
        />}
        {doc && mediaOpen && <><div className="lp-media-return"><button type="button" onClick={() => {if(window.dispatchEvent(new Event('clicko:studio-before-leave',{cancelable:true})))setMediaOpen(false);}}>Voltar ao canvas de camadas</button>{projectButtons}</div>
            <CanonicalVideoEditor key={doc.documentId} doc={doc as unknown as CraftDocument} assets={[...extraAssets,...(data.snapshot?.assets||[])].filter((asset,index,rows)=>rows.findIndex(row=>row.id===asset.id)===index)} visible onDocument={value=>adopt(value as unknown as LocalDocument)} onUpload={()=>file.current?.click()} onLibrary={()=>file.current?.click()} userId={userId}/>
        </>}
        <StudioUtilityPanel title="Projetos" open={utility==='projects'} onClose={()=>setUtility(null)}>
            <div className="lp-project-picker"><ClickoSelectMenu value={doc?.documentId||''} options={[{value:'',label:'Selecionar projeto'},...options]} onChange={id=>{
                if(!locked&&!dirty){const found=projects.find(row=>row.documentId===id);if(found){adopt(found);setUtility(null);}}
            }} ariaLabel="Projeto local" disabled={locked||dirty}/></div>
            <button type="button" disabled={locked||dirty} onClick={()=>{setDoc(undefined);setTasks([]);setSelected(undefined);setDownload(undefined);setJob(undefined);setUtility(null);}}>Novo projeto</button>
            {dirty && <p>Salve as alterações antes de abrir outro projeto.</p>}
        </StudioUtilityPanel>
        <StudioUtilityPanel title="Histórico" open={utility==='history'} onClose={()=>setUtility(null)}>
            <h3>Versões do projeto · {versions.length}</h3>
            {versions.map(version=><div className="lp-version" key={version.number}><span>v{version.number} · {version.label}</span><button type="button" disabled={locked||dirty} onClick={()=>void run(async()=>adopt(await productApi.restoreStudioDocumentVersion(doc!.documentId,version.number,doc!.revision) as LocalDocument))}>Restaurar</button></div>)}
            <details className="lp-task-history"><summary>Histórico dos agentes · {tasks.length} tarefas</summary>{tasks.map(task=><article key={task.id}><strong>{task.role} · {task.status}{task.appliedRevision ? ' · aplicado na revisão '+task.appliedRevision : ''}</strong><p>{task.instruction}</p><small>{task.id} · {task.provider} · custo externo R$ 0</small>{task.history?.map((event,index)=><p key={index}>{event.type} · {event.at}</p>)}</article>)}</details>
        </StudioUtilityPanel>
        <StudioUtilityPanel title="Projeto e ferramentas" open={utility==='project'} onClose={()=>setUtility(null)}>
            {page && doc && <><p>{doc.title} · revisão {doc.revision}</p><label>Fundo do projeto<input disabled={locked} type="color" value={page.background.slice(0,7)} onChange={event=>change({...doc.composition,pages:[{...page,background:event.target.value}]})}/></label>
                {dirty&&!pending&&<button type="button" disabled={busy} onClick={()=>void run(async()=>{localStorage.setItem(storageKey+':previous',JSON.stringify(doc));adopt(await localApi.document(doc.documentId));setNotice('Versão salva recarregada. Rascunho anterior preservado como backup local.');})}>Recarregar versão salva</button>}</>}
            <details className="lp-settings"><summary>Modelos dos agentes</summary><p>A KLIC mantém sua configuração Gemini. Cada especialista pode usar regras locais ou uma conexão Ollama já instalada. Nenhum modelo é baixado por este painel.</p>{roles && (['audiovisual', 'image'] as const).map(role => <label key={role}>{role === 'audiovisual' ? 'Audiovisual' : 'Imagem'}<ClickoSelectMenu ariaLabel={`Modelo do agente ${role}`} disabled={busy || !canConfigure} value={roles[role].mode === 'local_model' ? `${roles[role].connectionId}|${roles[role].model}` : 'local_tools'} options={[{ value: 'local_tools', label: 'Ferramentas locais · sem inferência' }, ...usableConnections.flatMap(connection => connection.config.models.filter(model => !model.toLowerCase().includes('cloud')).map(model => ({ value: `${connection.id}|${model}`, label: `${connection.label} · ${model}` })))]} onChange={value => { const [connectionId, model] = value.split('|'); setRoles({ ...roles, [role]: value === 'local_tools' ? { mode: 'local_tools' } : { mode: 'local_model', connectionId, model } }); }}/></label>)}<button disabled={busy || !roles || !canConfigure} onClick={() => void run(async () => { setRoles(await localApi.configure(workspaceId, roles!)); setNotice('Configuração dos agentes salva.'); })}>Salvar configuração</button><details><summary>Registrar Ollama local existente</summary><label>ID do modelo instalado<input ref={modelField} placeholder="qwen3:0.6b"/></label><button disabled={busy || !canConfigure} onClick={() => void run(async () => { const model = modelField.current?.value.trim(); if (!model)
        throw new Error('Informe o ID exato de um modelo já instalado.'); const connection = await craftApi.saveLLMConnection(workspaceId, { label: 'Ollama local', provider: 'ollama', protocol: 'ollama_chat', baseUrl: 'http://127.0.0.1:11434', models: [model], authHeader: 'Authorization', authPrefix: 'Bearer', enabled: true, billingMode: 'local_free', budgetUsd: 0, inputUsdPerMillion: 0, outputUsdPerMillion: 0, maxOutputTokens: 3000 }); setConnections(rows => [...rows, connection]); setNotice('Conexão registrada. A disponibilidade será verificada antes da inferência.'); })}>Registrar conexão</button></details></details>
        </StudioUtilityPanel>
        <StudioUtilityPanel title="Produção assistida" open={utility==='production'} onClose={()=>setUtility(null)}>
            <StudioKlicButton/><p>A conversa KLIC é compartilhada com a plataforma. Use abaixo apenas para preparar e revisar um plano de ferramentas.</p>
            {selected&&<p>Alvo: {layer?.name||'camada selecionada'} <button type="button" disabled={locked} onClick={()=>setSelected(undefined)}>Desmarcar · editar projeto inteiro</button></p>}
            {planningForm}
            {tasks[0]&&<section className="lp-plan" aria-label="Plano do agente"><strong>{tasks[0].role==='image'?'Agente visual':'Agente audiovisual'}</strong><p>{tasks[0].result?.rationale||tasks[0].errorCode}</p><details><summary>Detalhes do plano</summary><small>{tasks[0].provider} · {tasks[0].result?.commands?.length||0} operações · {tasks[0].result?.state}</small></details><button type="button" disabled={locked||dirty||!tasks[0].result?.commands?.length||tasks[0].status!=='succeeded'||tasks[0].documentRevision!==doc?.revision} onClick={()=>void run(()=>apply(tasks[0]))}>Aplicar plano</button></section>}
        </StudioUtilityPanel>
        <StudioUtilityPanel title="Exportação" open={utility==='output'} onClose={()=>setUtility(null)}>
            {rendering&&<p role="status">Renderizando… {job?.progress}% <button type="button" onClick={()=>void run(async()=>setJob(await apiFetch(localBase+'/jobs/'+job!.id+'/cancel',{method:'POST',body:JSON.stringify({reason:'Cancelado pelo usuário'})})))}>Cancelar</button></p>}
            {job?.status==='failed'&&<p role="alert">{job.errorMessage||job.errorCode}</p>}
            {download&&<section className="lp-output"><video controls playsInline src={download}/><a href={download+(download.includes('?')?'&':'?')+'download=1'} download>Baixar MP4</a></section>}
            {!rendering&&!download&&job?.status!=='failed'&&<p>A exportação concluída aparecerá aqui.</p>}
        </StudioUtilityPanel>
    </section>;
}
