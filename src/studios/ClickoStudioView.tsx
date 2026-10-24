import React from 'react';
import { ProductDataProvider } from '../context/ProductDataContext';
import { useOperations } from '../context/OperationsContext';
import { CraftStudio } from './craft/CraftStudio';
import type { NavigationTab } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import type { StudioTool, StudioToolId } from './studioNavigation';
import './clicko-studio.css';
import './shared/studio-experience.css';

const VideoStudio = React.lazy(() => import('./video/VideoStudio').then(module => ({ default: module.VideoStudio })));
const ImageStudio = React.lazy(() => import('./image/ImageStudio').then(module => ({ default: module.ImageStudio })));
const LocalProductionStudio = React.lazy(() => import('./local/LocalProductionStudio').then(module => ({ default: module.LocalProductionStudio })));

export function ClickoStudioView({ module, onNavigate, tool, onToolChange }: { module: 'create-image' | 'create-video'; onNavigate: (tab: NavigationTab) => void; tool?: StudioTool; onToolChange?: (id: StudioToolId) => void }) {
  const { activeClient, studioHandoff } = useOperations();
  const { activeAccount, currentUser } = useGovernance();
  const [nativeDocument, setNativeDocument] = React.useState<string>();
  const [advanced, setAdvanced] = React.useState(false);
  const localEligible = tool && ['video-motion', 'image-edit', 'image-composition'].includes(tool.id);
  React.useEffect(() => setAdvanced(false), [tool?.id]);
  React.useEffect(() => setNativeDocument(undefined), [module, activeClient?.id, activeAccount.workspaceId, currentUser?.id]);
  const navigate = (url: string) => {
    const target = new URL(url, window.location.origin);
    if (target.pathname === '/studios/native') {
      if (!target.searchParams.has('mode')) target.searchParams.set('mode', module === 'create-video' ? 'video' : 'visual');
      setNativeDocument(target.search); return;
    }
    if (target.pathname.startsWith('/approvals')) onNavigate('approvals');
    else if (target.pathname.startsWith('/content') || target.pathname.startsWith('/library')) onNavigate('library');
    else if (target.pathname === '/brand-memory') onNavigate('workspace');
    else setNativeDocument(undefined);
  };
  return <div data-clicko-studio={module} data-clicko-studio-client={activeClient?.id || ''} className="mx-auto w-full max-w-[1560px] p-3 sm:p-6" key={`${currentUser?.id}:${activeAccount.workspaceId}:${module}:${activeClient?.id || ''}`}>
    <ProductDataProvider module={module}>
      {localEligible && <details className="lp-editor-choice"><summary>Ferramentas do Studio</summary><div>
        <button aria-pressed={!advanced} onClick={event => { if (window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable:true }))) {setAdvanced(false);event.currentTarget.closest('details')?.removeAttribute('open');} }}>Canvas de camadas local</button>
        <button aria-pressed={advanced} onClick={event => { if (window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable:true }))) {setAdvanced(true);event.currentTarget.closest('details')?.removeAttribute('open');} }}>Recursos nativos existentes</button>
        <p>Os motores nativos dependem de runtime. Seus formatos e projetos existentes são preservados, sem conversão automática.</p>
      </div></details>}
      {localEligible && !advanced
        ? <React.Suspense fallback={<p role="status">Carregando produção local…</p>}><LocalProductionStudio module={module} onNavigate={onNavigate}/></React.Suspense>
        : module === 'create-video'
        ? <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de vídeo…</div>}><VideoStudio embedded={Boolean(tool)} requestedArea={tool?.module === 'create-video' ? tool.entry : undefined} onAreaChange={area => onToolChange?.(({ ai:'video-create', editor:'video-edit', motion:'video-motion', ad:'ad-create' } as const)[area])} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} onLibrary={() => onNavigate('library')} onApprovals={() => onNavigate('approvals')} /></React.Suspense>
        : nativeDocument
        ? <CraftStudio pathname="/studios/native" search={nativeDocument} navigate={navigate} returnTo="/image" />
        : <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de imagens…</div>}><ImageStudio embedded={Boolean(tool)} requestedEntry={tool?.module === 'create-image' ? tool.entry : undefined} onModeChange={mode => onToolChange?.(mode === 'edit' ? 'image-edit' : tool?.id === 'ad-creatives' ? 'ad-creatives' : 'image-generate')} onEditorial={() => onToolChange?.('image-editorial')} onNavigate={onNavigate} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} /></React.Suspense>}
    </ProductDataProvider>
  </div>;
}
