import React from 'react';
import {
  BrainCircuit,
  FileText,
  Image as ImageIcon,
  Video,
  Target,
  Sparkles,
  FileEdit,
  Wand2,
  ChevronRight
} from 'lucide-react';
import { CreationStudioView } from './CreationStudioView';
import { ImageStudioView } from './ImageStudioView';
import { VideoEditorView } from './VideoEditorView';
import { CreativeMatrixView } from './CreativeMatrixView';
import { SmartBriefingView } from './SmartBriefingView';
import { useOperations } from '../context/OperationsContext';
import type { Post } from '../types';

export type StudioModuleId = 'create' | 'edit_image' | 'edit_video' | 'matrix' | 'briefing';

interface StudioViewProps {
  onSavePost: (post: Partial<Post>) => void;
  initialMode?: StudioModuleId;
}

export function StudioView({ onSavePost, initialMode = 'create' }: StudioViewProps) {
  const { brain, campaigns, activeCampaign, setActiveCampaignId } = useOperations();
  const [mode, setMode] = React.useState<StudioModuleId>(initialMode);

  React.useEffect(() => {
    if (initialMode) {
      setMode(initialMode);
    }
  }, [initialMode]);

  const tabs = [
    {
      id: 'create' as const,
      label: 'Criar Conteúdo',
      sublabel: 'Copys, Posts, Carrosséis & Anúncios',
      icon: FileText,
      badge: 'Redação & Agendamento',
    },
    {
      id: 'edit_image' as const,
      label: 'Editar Imagem IA',
      sublabel: 'Remover fundo, Upscale & Expansão',
      icon: ImageIcon,
      badge: 'Editor Visual Completo',
    },
    {
      id: 'edit_video' as const,
      label: 'Vídeo IA & Shorts',
      sublabel: 'Cortes, Legendas & Dublagem',
      icon: Video,
      badge: 'Editor de Vídeo Pro',
    },
    {
      id: 'matrix' as const,
      label: 'Matriz Criativa',
      sublabel: 'Gancho, Ângulo, Emoção & CTA',
      icon: Target,
      badge: 'Engenharia de Conversão',
    },
    {
      id: 'briefing' as const,
      label: 'Briefing Inteligente',
      sublabel: 'Planejamento & Cronogramas',
      icon: FileEdit,
      badge: 'Estratégia & Metas',
    },
  ];

  return (
    <div className="min-h-screen space-y-5 pb-10">
      {/* Top Header */}
      <div className="mx-auto flex w-full max-w-[1600px] flex-wrap items-center justify-between gap-5 px-6 pt-6 2xl:px-8 2xl:pt-7">
        <div className="space-y-1.5">
          <p className="text-[10px] font-mono uppercase tracking-[0.25em] font-bold text-[#8bd132] flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5" /> Central de Produção Multimídia & IA
          </p>
          <h1 className="text-[26px] font-semibold tracking-tight text-white">Clicko Creative Studio</h1>
          <p className="text-xs text-[#717d85] max-w-xl">
            Suíte profissional para mídias sociais dividida em módulos independentes com ferramentas e fluxos exclusivos.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-2 rounded-xl border border-[#8bd132]/30 bg-[#8bd132]/[0.08] px-4 py-2.5 text-[10px] font-mono font-bold text-[#8bd132] shadow-sm">
            <BrainCircuit className="h-4 w-4" /> Brain Memória Rev. {brain.revision}
          </span>
          <select
            value={activeCampaign?.id || ''}
            onChange={(e) => setActiveCampaignId(e.target.value || undefined)}
            className="h-10 rounded-xl border border-white/[0.08] bg-[#070a0d] px-4 text-xs font-semibold text-white outline-none focus:border-[#8bd132]/50 transition-all"
          >
            <option value="">Sem campanha vinculada</option>
            {campaigns.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>
                {campaign.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Module Navigation Cards */}
      <div className="custom-scrollbar mx-auto flex w-full max-w-[1600px] gap-3 overflow-x-auto px-6 pb-1 sm:grid sm:grid-cols-2 sm:overflow-visible lg:grid-cols-5 2xl:px-8">
        {tabs.map(({ id, label, sublabel, icon: Icon, badge }) => {
          const isActive = mode === id;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setMode(id)}
              className={`group relative flex min-w-[210px] flex-col justify-between rounded-xl border p-4 text-left transition-colors duration-150 sm:min-w-0 ${
                isActive
                  ? 'border-[#8bd132]/35 bg-[#101510]'
                  : 'bg-[#070a0d] border-white/[0.05] hover:bg-[#0e1318] hover:border-white/20'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`grid h-10 w-10 place-items-center rounded-xl border ${
                      isActive
                        ? 'border-[#8bd132]/40 bg-[#8bd132]/15 text-[#8bd132]'
                        : 'border-white/10 bg-white/[0.03] text-[#717d85] group-hover:text-white'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </span>
                  <span
                    className={`text-[9px] font-mono font-semibold px-2 py-0.5 rounded-full border ${
                      isActive
                        ? 'border-[#8bd132]/30 bg-[#8bd132]/10 text-[#8bd132]'
                        : 'border-white/[0.06] bg-white/[0.02] text-[#627078]'
                    }`}
                  >
                    {badge}
                  </span>
                </div>

                <h3 className={`text-sm font-extrabold tracking-tight ${isActive ? 'text-white' : 'text-[#c0c8ce] group-hover:text-white'}`}>
                  {label}
                </h3>
                <p className={`mt-1 text-[11px] leading-relaxed ${isActive ? 'text-[#8bd132]' : 'text-[#627078]'}`}>
                  {sublabel}
                </p>
              </div>

              <div className="mt-4 flex items-center gap-1 text-[10px] font-bold text-[#8bd132] opacity-0 group-hover:opacity-100 transition-opacity">
                <span>Acessar Módulo</span>
                <ChevronRight className="h-3 w-3" />
              </div>

              {isActive && (
                <div className="absolute inset-x-3 top-0 h-0.5 rounded-b-full bg-[#8bd132]" />
              )}
            </button>
          );
        })}
      </div>

      {/* Embedded Studio Module Workspace */}
      <div className="mx-auto w-full max-w-[1600px] px-1 sm:px-2">
        {mode === 'create' && (
          <CreationStudioView
            onSavePost={(post) =>
              onSavePost({
                ...post,
                campaignId: activeCampaign?.id,
                strategyId: activeCampaign?.id,
                brainRevision: brain.revision,
                origin: activeCampaign ? 'strategy' : 'brain',
                objective: activeCampaign?.objective,
              })
            }
          />
        )}

        {mode === 'edit_image' && <ImageStudioView />}

        {mode === 'edit_video' && <VideoEditorView />}

        {mode === 'matrix' && <CreativeMatrixView onSavePost={onSavePost} />}

        {mode === 'briefing' && <SmartBriefingView />}
      </div>
    </div>
  );
}

