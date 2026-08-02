import React from 'react';
import { BrainCircuit, FileText, Image, Video } from 'lucide-react';
import { CreationStudioView } from './CreationStudioView';
import { ImageStudioView } from './ImageStudioView';
import { VideoEditorView } from './VideoEditorView';
import { useOperations } from '../context/OperationsContext';
import type { Post } from '../types';

export function StudioView({ onSavePost }: { onSavePost: (post: Partial<Post>) => void }) {
  const { brain, campaigns, activeCampaign, setActiveCampaignId } = useOperations();
  const [mode, setMode] = React.useState<'content' | 'image' | 'video'>('content');
  return <div>
    <div className="mx-auto flex w-full max-w-[1480px] flex-wrap items-center justify-between gap-3 px-6 pt-6 2xl:px-10 2xl:pt-10"><div><p className="text-[10px] uppercase tracking-[0.24em] text-[#8bd132]">Produção multimídia conectada</p><h1 className="mt-1 text-2xl font-semibold text-white">Studio</h1></div><div className="flex flex-wrap items-center gap-2"><span className="flex items-center gap-1.5 rounded-lg border border-[#8bd132]/20 bg-[#8bd132]/[0.06] px-3 py-2 text-[9px] text-[#8bd132]"><BrainCircuit className="h-3.5 w-3.5" />Brain rev. {brain.revision}</span><select value={activeCampaign?.id || ''} onChange={(e) => setActiveCampaignId(e.target.value || undefined)} className="h-9 rounded-lg border border-white/[0.07] bg-[#182126] px-3 text-[9px] text-white outline-none"><option value="">Sem campanha vinculada</option>{campaigns.map((campaign) => <option key={campaign.id} value={campaign.id}>{campaign.name}</option>)}</select></div></div>
    <div className="mx-auto mt-4 flex w-full max-w-[1480px] gap-1 px-6 2xl:px-10">{[{ id: 'content' as const, label: 'Conteúdo e copy', icon: FileText }, { id: 'image' as const, label: 'Imagem', icon: Image }, { id: 'video' as const, label: 'Vídeo', icon: Video }].map(({ id, label, icon: Icon }) => <button key={id} onClick={() => setMode(id)} className={`flex items-center gap-2 rounded-lg px-4 py-2.5 text-[10px] ${mode === id ? 'bg-[#8bd132] font-bold text-[#14200e]' : 'bg-[#182126] text-[#aeb6ba]'}`}><Icon className="h-4 w-4" />{label}</button>)}</div>
    <div className="studio-embedded">{mode === 'content' && <CreationStudioView onSavePost={(post) => onSavePost({ ...post, campaignId: activeCampaign?.id, strategyId: activeCampaign?.id, brainRevision: brain.revision, origin: activeCampaign ? 'strategy' : 'brain', objective: activeCampaign?.objective })} />}{mode === 'image' && <ImageStudioView />}{mode === 'video' && <VideoEditorView />}</div>
  </div>;
}
