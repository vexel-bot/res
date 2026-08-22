import React from 'react';
import { BrainCircuit, FileEdit, FileText, Image as ImageIcon, Sparkles, Target, Video, X } from 'lucide-react';
import { CreationStudioView } from './CreationStudioView';
import { ImageStudioView } from './ImageStudioView';
import { VideoEditorView } from './VideoEditorView';
import { CreativeMatrixView } from './CreativeMatrixView';
import { SmartBriefingView } from './SmartBriefingView';
import { useOperations } from '../context/OperationsContext';
import type { Post } from '../types';
import type { StudioModuleId } from './StudioView';

interface StudioViewProps {
  onSavePost: (post: Partial<Post>) => void;
  initialMode?: StudioModuleId;
}

const modules = [
  { id: 'create' as const, label: 'Criar conteúdo', short: 'Texto e publicação', icon: FileText },
  { id: 'edit_image' as const, label: 'Imagem IA', short: 'Criação e edição', icon: ImageIcon },
  { id: 'edit_video' as const, label: 'Vídeo IA', short: 'Cortes e legendas', icon: Video },
  { id: 'matrix' as const, label: 'Matriz criativa', short: 'Conversão e testes', icon: Target },
  { id: 'briefing' as const, label: 'Briefing', short: 'Plano e cronograma', icon: FileEdit },
];

const moduleDescriptions: Record<StudioModuleId, { eyebrow: string; title: string; description: string }> = {
  create: { eyebrow: 'Produção assistida', title: 'Crie sem sair do fluxo.', description: 'Texto, mídia, canal e agenda convivem em uma única área de trabalho.' },
  edit_image: { eyebrow: 'Laboratório visual', title: 'Imagem com precisão.', description: 'Ferramentas de IA priorizadas ao redor da peça, sem distrações.' },
  edit_video: { eyebrow: 'Edição audiovisual', title: 'Vídeo em ritmo de publicação.', description: 'Cortes, legendas e acabamento organizados como uma bancada profissional.' },
  matrix: { eyebrow: 'Engenharia criativa', title: 'Estratégia que vira peça.', description: 'Combine ângulo, emoção e CTA com leitura visual imediata.' },
  briefing: { eyebrow: 'Direção de campanha', title: 'Clareza antes da criação.', description: 'Transforme objetivos em um plano executável sem quebrar o contexto.' },
};

export function StudioView({ onSavePost, initialMode = 'create' }: StudioViewProps) {
  const { brain, activeClient, campaigns, activeCampaign, studioHandoff, setActiveCampaignId, clearStudioHandoff } = useOperations();
  const [mode, setMode] = React.useState<StudioModuleId>(initialMode);

  React.useEffect(() => {
    if (initialMode) setMode(initialMode);
  }, [initialMode]);

  React.useEffect(() => {
    if (studioHandoff) setMode('create');
  }, [studioHandoff?.id]);

  const description = moduleDescriptions[mode];

  return (
    <div className="clicko-studio-immersive min-h-[calc(100vh-72px)] lg:grid lg:grid-cols-[232px_minmax(0,1fr)]">
      <aside className="clicko-studio-sidebar custom-scrollbar border-b border-white/[0.06] px-5 py-5 lg:sticky lg:top-[72px] lg:h-[calc(100vh-80px)] lg:overflow-y-auto lg:border-b-0 lg:border-r lg:px-4 lg:py-7">
        <div className="px-2">
          <div className="flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.22em] text-[#ff5c5c]"><Sparkles className="h-3.5 w-3.5" />Creative OS</div>
          <h1 className="mt-2 text-[21px] font-medium tracking-[-0.035em] text-white">Studio</h1>
          <p className="mt-2 text-[10px] leading-4 text-[#657178]">Escolha uma bancada e mantenha o foco no trabalho.</p>
        </div>

        <nav className="custom-scrollbar mt-5 flex gap-1 overflow-x-auto pb-1 lg:block lg:space-y-1 lg:overflow-visible">
          {modules.map(({ id, label, short, icon: Icon }, index) => {
            const active = mode === id;
            return (
              <button key={id} type="button" onClick={() => setMode(id)} aria-pressed={active} className={`clicko-interactive-surface group relative flex min-w-[168px] items-center gap-3 rounded-md border border-transparent px-2.5 py-2.5 text-left lg:w-full lg:min-w-0 ${active ? 'bg-white/[0.055]' : 'hover:bg-white/[0.025]'}`}>
                {active && <span className="absolute inset-y-2 left-0 w-px bg-[#ff5c5c]" />}
                <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-md border ${active ? 'border-[#ff5c5c]/25 bg-[#ff5c5c]/10 text-[#ff5c5c]' : 'border-white/[0.06] text-[#68747b] group-hover:text-white'}`}><Icon className="h-3.5 w-3.5" /></span>
                <span className="min-w-0"><span className={`block truncate text-[10px] font-medium ${active ? 'text-white' : 'text-[#909aa0]'}`}>{label}</span><span className="mt-0.5 block truncate text-[8px] text-[#515d64]">0{index + 1} · {short}</span></span>
              </button>
            );
          })}
        </nav>

        <div className="mt-6 border-t border-white/[0.06] px-2 pt-5">
          <label className="text-[8px] font-medium uppercase tracking-[0.18em] text-[#58646b]">Campanha ativa</label>
          <select value={activeCampaign?.id || ''} onChange={(event) => setActiveCampaignId(event.target.value || undefined)} className="mt-2 h-9 w-full rounded-md border border-white/[0.07] bg-transparent px-2.5 text-[9px] text-[#b8c0c4] outline-none focus:border-[#ff5c5c]/40">
            <option value="">Sem campanha</option>
            {campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}
          </select>
          <div className="mt-4 flex items-center gap-2 text-[8px] text-[#5f6b72]"><BrainCircuit className="h-3.5 w-3.5 text-[#ff5c5c]" /><span>Memória da marca · revisão {brain.revision}</span></div>
          {activeClient && <div className="mt-2 truncate text-[8px] text-[#6f6f6f]">Cliente · <span className="text-[#aaa]">{activeClient.name}</span></div>}
        </div>
      </aside>

      <main className="min-w-0">
        <header className="clicko-studio-workspace-header flex flex-col gap-4 border-b border-white/[0.06] px-6 py-6 md:flex-row md:items-end md:justify-between 2xl:px-9 2xl:py-8">
          <div>
            <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-[#ff5c5c]">{description.eyebrow}</span>
            <h2 className="mt-2 text-[clamp(24px,2.4vw,38px)] font-medium leading-tight tracking-[-0.04em] text-white">{description.title}</h2>
            <p className="mt-2 max-w-2xl text-[11px] leading-5 text-[#707c83]">{description.description}</p>
          </div>
          <div className="flex items-center gap-2 text-[8px] uppercase tracking-[0.16em] text-[#556168]"><span className="h-1.5 w-1.5 rounded-full bg-[#ff5c5c]" />Contexto sincronizado</div>
        </header>

        {studioHandoff && <section className="clicko-studio-handoff mx-3 mt-3 rounded-xl border border-[#ff5c5c]/20 bg-[#ff5c5c]/[0.045] px-4 py-3 sm:mx-4 2xl:mx-6"><div className="flex flex-wrap items-start justify-between gap-3"><div className="flex min-w-0 gap-3"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#ff5c5c]/10 text-[#ff7c7c]"><Sparkles className="h-4 w-4" /></span><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><span className="text-[8px] font-semibold uppercase tracking-[0.16em] text-[#ff7c7c]">Contexto recebido</span><span className="rounded-full bg-white/[0.04] px-2 py-0.5 text-[7px] uppercase text-[#777]">{studioHandoff.source}</span></div><strong className="mt-1 block truncate text-[10px] text-white">{studioHandoff.title}</strong><p className="mt-1 line-clamp-2 text-[8px] leading-relaxed text-[#999]">{studioHandoff.objective} · {studioHandoff.hook}</p></div></div><button onClick={clearStudioHandoff} aria-label="Dispensar contexto recebido" className="grid h-7 w-7 place-items-center rounded-lg text-[#777] hover:bg-white/[0.05] hover:text-white"><X className="h-3.5 w-3.5" /></button></div></section>}

        <div className="clicko-studio-canvas min-w-0 px-3 pb-10 pt-3 sm:px-4 2xl:px-6">
          {mode === 'create' && <CreationStudioView onSavePost={(post) => onSavePost({ ...post, clientId: activeClient?.id, campaignId: activeCampaign?.id, strategyId: activeCampaign?.id, brainRevision: brain.revision, origin: studioHandoff?.source === 'analytics' ? 'analytics' : activeCampaign ? 'strategy' : 'brain', objective: studioHandoff?.objective || activeCampaign?.objective })} />}
          {mode === 'edit_image' && <ImageStudioView />}
          {mode === 'edit_video' && <VideoEditorView />}
          {mode === 'matrix' && <CreativeMatrixView onSavePost={onSavePost} />}
          {mode === 'briefing' && <SmartBriefingView />}
        </div>
      </main>
    </div>
  );
}
