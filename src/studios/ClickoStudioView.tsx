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
const DepartmentStudio = React.lazy(() => import('./department/DepartmentStudio').then(module => ({ default: module.DepartmentStudio })));

export function ClickoStudioView({ module, onNavigate, tool, onToolChange }: { module: 'create-image' | 'create-video'; onNavigate: (tab: NavigationTab) => void; tool?: StudioTool; onToolChange?: (id: StudioToolId) => void }) {
  const { activeClient, studioHandoff } = useOperations();
  const { activeAccount, currentUser } = useGovernance();
  const [nativeDocument, setNativeDocument] = React.useState<string>();
  const craftMode = tool?.id === 'video-motion' ? 'effects'
    : tool?.id === 'video-edit' ? 'video'
    : tool?.id === 'image-edit' || tool?.id === 'image-composition' ? 'visual' : undefined;
  const castQuery = new URLSearchParams(window.location.search);
  const castVideoRequest = tool?.id === 'video-create' && (castQuery.has('identityVersion') || castQuery.has('voiceVersion'));
  React.useEffect(() => setNativeDocument(undefined), [module, tool?.id, activeClient?.id, activeAccount.workspaceId, currentUser?.id]);
  const navigate = (url: string) => {
    const target = new URL(url, window.location.origin);
    if (target.pathname === '/studios/native') {
      if (!target.searchParams.has('mode')) target.searchParams.set('mode', craftMode || (module === 'create-video' ? 'video' : 'visual'));
      setNativeDocument(target.search); return;
    }
    if (target.pathname === '/video' && module === 'create-video') { setNativeDocument(undefined); onToolChange?.('video-create'); return; }
    if (target.pathname === '/image' && module === 'create-image') { setNativeDocument(undefined); onToolChange?.('image-generate'); return; }
    if (target.pathname.startsWith('/approvals')) onNavigate('approvals');
    else if (target.pathname.startsWith('/content') || target.pathname.startsWith('/library')) onNavigate('library');
    else if (target.pathname === '/brand-memory') onNavigate('workspace');
    else setNativeDocument(undefined);
  };
  return <div data-clicko-studio={module} data-clicko-studio-client={activeClient?.id || ''} className="mx-auto w-full max-w-[1560px] p-3 sm:p-6" key={`${currentUser?.id}:${activeAccount.workspaceId}:${module}:${activeClient?.id || ''}`}>
    <ProductDataProvider module={module}>
      {castVideoRequest
        ? <React.Suspense fallback={<p role="status">Carregando o pedido com aparência e voz…</p>}><DepartmentStudio mode="video" /></React.Suspense>
        : nativeDocument || craftMode
        ? <CraftStudio key={tool?.id || module} pathname="/studios/native" search={nativeDocument || (() => {
            const params = new URLSearchParams(window.location.search);
            if (craftMode) params.set('mode', craftMode);
            return '?' + params.toString();
          })()} navigate={navigate} returnTo={module === 'create-video' ? '/video' : '/image'} />
        : module === 'create-video'
        ? <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de vídeo…</div>}><VideoStudio embedded={Boolean(tool)} requestedArea={tool?.module === 'create-video' ? tool.entry : undefined} onAreaChange={area => onToolChange?.(({ ai:'video-create', editor:'video-edit', motion:'video-motion', ad:'ad-create' } as const)[area])} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} onLibrary={() => onNavigate('library')} onApprovals={() => onNavigate('approvals')} /></React.Suspense>
        : <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de imagens…</div>}><ImageStudio embedded={Boolean(tool)} requestedEntry={tool?.module === 'create-image' ? tool.entry : undefined} onModeChange={mode => onToolChange?.(mode === 'edit' ? 'image-edit' : tool?.id === 'ad-creatives' ? 'ad-creatives' : 'image-generate')} onEditorial={() => onToolChange?.('image-editorial')} onNavigate={onNavigate} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} /></React.Suspense>}
    </ProductDataProvider>
  </div>;
}
