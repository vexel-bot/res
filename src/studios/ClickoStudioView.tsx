import React from 'react';
import { ProductDataProvider } from '../context/ProductDataContext';
import { useOperations } from '../context/OperationsContext';
import type { NavigationTab } from '../types';
import { useGovernance } from '../context/GovernanceContext';
import { ImageProjectArchive } from './image/ImageProjectArchive';
import type { StudioTool, StudioToolId } from './studioNavigation';
import './clicko-studio.css';
import './shared/studio-experience.css';

const VideoAssemblyStudio = React.lazy(() => import('./video/VideoAssemblyStudio').then(module => ({ default: module.VideoAssemblyStudio })));
const ImageStudio = React.lazy(() => import('./image/ImageStudio').then(module => ({ default: module.ImageStudio })));
const DepartmentStudio = React.lazy(() => import('./department/DepartmentStudio').then(module => ({ default: module.DepartmentStudio })));

export function ClickoStudioView({ module, onNavigate, tool, onToolChange }: { module: 'create-image' | 'create-video'; onNavigate: (tab: NavigationTab) => void; tool?: StudioTool; onToolChange?: (id: StudioToolId) => void }) {
  const { activeClient, studioHandoff } = useOperations();
  const { activeAccount, currentUser } = useGovernance();
  const query = new URLSearchParams(window.location.search);
  const castVideo = tool?.id === 'video-create' && (query.has('identityVersion') || query.has('voiceVersion'));
  return <div data-clicko-studio={module} data-clicko-studio-client={activeClient?.id || ''} className="mx-auto w-full max-w-[1560px] p-3 sm:p-6" key={`${currentUser?.id}:${activeAccount.workspaceId}:${module}:${activeClient?.id || ''}`}>
    <ProductDataProvider module={module}>
      {castVideo
        ? <React.Suspense fallback={<p role="status">Carregando a apresentação…</p>}><DepartmentStudio mode="video" /></React.Suspense>
        : module === 'create-video'
        ? <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de vídeo…</div>}><VideoAssemblyStudio initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} /></React.Suspense>
        : tool?.id === 'image-composition' ? <ImageProjectArchive />
        : <React.Suspense fallback={<div role="status" className="p-4 text-sm">Carregando estúdio de imagens…</div>}><ImageStudio embedded={Boolean(tool)} requestedEntry={tool?.module === 'create-image' ? tool.entry : undefined} onModeChange={mode => onToolChange?.(mode === 'edit' ? 'image-edit' : tool?.id === 'ad-creatives' ? 'ad-creatives' : 'image-generate')} onEditorial={() => onToolChange?.('image-editorial')} onNavigate={onNavigate} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} /></React.Suspense>}
    </ProductDataProvider>
  </div>;
}
