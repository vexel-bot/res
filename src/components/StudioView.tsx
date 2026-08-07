import React from 'react';
import {
  BrainCircuit,
  FileText,
  Image as ImageIcon,
  Video,
  Target,
  Sparkles,
  Layers,
  Wand2,
  FileEdit
} from 'lucide-react';
import { CreationStudioView } from './CreationStudioView';
import { ImageStudioView } from './ImageStudioView';
import { VideoEditorView } from './VideoEditorView';
import { CreativeMatrixView } from './CreativeMatrixView';
import { SmartBriefingView } from './SmartBriefingView';
import { useOperations } from '../context/OperationsContext';
import type { Post } from '../types';

export function StudioView({ onSavePost }: { onSavePost: (post: Partial<Post>) => void }) {
  const { brain, campaigns, activeCampaign, setActiveCampaignId } = useOperations();
  const [mode, setMode] = React.useState<'create' | 'edit_image' | 'edit_video' | 'matrix' | 'briefing'>('create');

  const tabs = [
    { id: 'create' as const, label: 'Criar Conteúdo', sublabel: 'Copys, Posts, Carrosséis & Anúncios', icon: FileText },
    { id: 'edit_image' as const, label: 'Editar Imagem IA', sublabel: 'Remover fundo, upscale & expansão', icon: ImageIcon },
    { id: 'edit_video' as const, label: 'Vídeo IA & Shorts', sublabel: 'Cortes, legendas & dublagem', icon: Video },
    { id: 'matrix' as const, label: 'Matriz Criativa', sublabel: 'Gancho, Ângulo, Emoção & CTA', icon: Target },
    { id: 'briefing' as const, label: 'Briefing Inteligente', sublabel: 'Planejamento & cronogramas', icon: FileEdit },
  ];

  return (
    <div className="space-y-8 pb-16 min-h-screen">
      {/* Top Header */}
      <div className="mx-auto flex w-full max-w-[1720px] flex-wrap items-center justify-between gap-6 px-8 pt-8 2xl:px-12 2xl:pt-10">
        <div className="space-y-1.5">
          <p className="text-[10px] font-mono uppercase tracking-[0.25em] font-bold text-[#8bd132] flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5" /> Central de Produção Multimídia & IA
          </p>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Clicko Creative Studio</h1>
          <p className="text-xs text-[#717d85] max-w-xl">
            Ambiente unificado de alta performance para criação, edição visual acelerada por IA e arquitetura de marca.
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

      {/* Module Selector Tabs */}
      <div className="mx-auto flex w-full max-w-[1720px] flex-wrap gap-3 px-8 2xl:px-12">
        {tabs.map(({ id, label, sublabel, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setMode(id)}
            className={`flex flex-col items-start rounded-2xl px-5 py-3.5 transition-all duration-200 border ${
              mode === id
                ? 'bg-[#8bd132] font-bold text-[#080e05] border-[#8bd132] shadow-[0_0_24px_rgba(139,209,50,0.3)] scale-[1.02]'
                : 'bg-[#070a0d] text-[#8e9aa2] hover:bg-[#0f141a] hover:text-white border-white/[0.05]'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Icon className="h-4 w-4" />
              <span className="text-xs font-bold tracking-tight">{label}</span>
            </div>
            <span
              className={`mt-1 text-[10px] ${
                mode === id ? 'text-[#1d2a13] font-semibold' : 'text-[#627078]'
              }`}
            >
              {sublabel}
            </span>
          </button>
        ))}
      </div>

      {/* Embedded Studio Modules Container */}
      <div className="mx-auto w-full max-w-[1720px] px-8 2xl:px-12">
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
