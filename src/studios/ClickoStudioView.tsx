import React from 'react';
import { ProductDataProvider } from '../context/ProductDataContext';
import { useOperations } from '../context/OperationsContext';
import { DepartmentStudio } from './department/DepartmentStudio';
import { CraftStudio } from './craft/CraftStudio';
import type { NavigationTab } from '../types';
import './clicko-studio.css';

export function ClickoStudioView({ module, onNavigate }: { module: 'create-image' | 'create-video'; onNavigate: (tab: NavigationTab) => void }) {
  const { activeClient, studioHandoff } = useOperations();
  const [nativeDocument, setNativeDocument] = React.useState<string>();
  React.useEffect(() => setNativeDocument(undefined), [module, activeClient?.id]);
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
  return <div data-clicko-studio={module} data-clicko-studio-client={activeClient?.id || ''} className="mx-auto w-full max-w-[1560px] p-3 sm:p-6" key={`${module}:${activeClient?.id || ''}`}>
    <ProductDataProvider module={module}>
      {nativeDocument
        ? <CraftStudio pathname="/studios/native" search={nativeDocument} navigate={navigate} returnTo={module === 'create-video' ? '/video' : '/image'} />
        : <DepartmentStudio mode={module === 'create-video' ? 'video' : 'image'} pathname={module === 'create-video' ? '/video' : '/image'} search="" navigate={navigate} initialBrief={studioHandoff ? { title: studioHandoff.title, objective: studioHandoff.objective } : undefined} />}
    </ProductDataProvider>
  </div>;
}
