import React from 'react';
import { INITIAL_POSTS, INITIAL_WORKSPACES } from '../data/mockData';
import type { BrandBrain, LibraryAsset, Post, StrategyCampaign, Workspace } from '../types';

type OperationsState = {
  brain: BrandBrain;
  campaigns: StrategyCampaign[];
  assets: LibraryAsset[];
  posts: Post[];
  activeCampaignId?: string;
};

type OperationsContextValue = OperationsState & {
  activeWorkspace: Workspace;
  activeCampaign?: StrategyCampaign;
  brainCompleteness: number;
  updateBrain: (values: Partial<BrandBrain>) => void;
  addBrainSource: (source: BrandBrain['sourceFiles'][number]) => void;
  createCampaign: (campaign: Omit<StrategyCampaign, 'id' | 'workspaceId' | 'brainRevision' | 'createdAt' | 'updatedAt'>) => StrategyCampaign;
  updateCampaign: (id: string, values: Partial<StrategyCampaign>) => void;
  setActiveCampaignId: (id?: string) => void;
  addPosts: (posts: Post[]) => void;
  updatePosts: React.Dispatch<React.SetStateAction<Post[]>>;
  addAsset: (asset: Omit<LibraryAsset, 'id' | 'workspaceId' | 'createdAt' | 'updatedAt'>) => LibraryAsset;
};

const activeWorkspace = INITIAL_WORKSPACES[0];
const storageKey = `clicko:operations:${activeWorkspace.id}`;
const now = () => new Date().toISOString();

const initialBrain: BrandBrain = {
  workspaceId: activeWorkspace.id,
  revision: 3,
  updatedAt: '2026-08-02T12:30:00.000Z',
  company: 'Clicko AI Studios é uma plataforma de operação de mídia com inteligência artificial para marcas e equipes de marketing.',
  products: 'Clicko Studio — planejamento, produção, aprovação, publicação e análise de mídia em um único fluxo.',
  services: 'Estratégia de conteúdo, automação editorial, criação multimídia, governança e inteligência de performance.',
  visualIdentity: 'Visual premium e tecnológico. Preto, branco, cinzas e verde sutil. Alto contraste, composições limpas e sem efeitos excessivos.',
  toneOfVoice: activeWorkspace.brandProfile.tone,
  audience: activeWorkspace.brandProfile.targetAudience,
  personas: 'Líder de marketing orientado a resultado; social media que precisa ganhar escala; fundador que quer consistência de marca.',
  objectives: 'Aumentar autoridade, gerar demanda qualificada e tornar a operação de mídia previsível e mensurável.',
  differentiators: 'Memória estratégica persistente, criação multimodal e rastreabilidade completa da estratégia ao resultado.',
  competitors: 'Suites de social media, ferramentas isoladas de IA generativa e plataformas de automação sem contexto de marca.',
  objections: 'Tempo de implantação, consistência das respostas de IA, governança e clareza sobre retorno do investimento.',
  pains: 'Ferramentas fragmentadas, briefing incompleto, retrabalho, demora em aprovações e dificuldade de atribuição.',
  desires: 'Produzir mais com qualidade, manter a marca consistente e transformar dados em próximas ações.',
  faq: 'Como o Brain é usado? Toda geração consulta a revisão ativa.\nComo funciona aprovação? Conteúdos mantêm comentários, histórico e versões.',
  requiredWords: 'Clicko AI Studios; operação de mídia; inteligência estratégica',
  forbiddenWords: 'promessas garantidas; linguagem sensacionalista; jargão sem explicação',
  history: 'Projeto iniciado como gerador de conteúdo e evoluído para sistema operacional de mídia com IA.',
  sourceLinks: ['https://clickostudio.com/'],
  sourceFiles: [
    { id: 'brain-logo', name: 'Identidade oficial Clicko', type: 'logo', addedAt: '2026-08-02T10:00:00.000Z' },
    { id: 'brain-guide', name: 'Guia de tom de voz.pdf', type: 'document', addedAt: '2026-08-02T10:15:00.000Z' },
  ],
};

const initialCampaigns: StrategyCampaign[] = [{
  id: 'strategy-q3', workspaceId: activeWorkspace.id, name: 'Lançamento Clicko Q3',
  objective: 'Gerar demanda qualificada para a nova experiência de operação de mídia com IA.',
  startDate: '2026-08-03', endDate: '2026-08-31', budget: 'R$ 18.000',
  kpis: ['Leads qualificados', 'CTR', 'Custo por reunião', 'Engajamento'],
  products: 'Clicko Studio', audience: 'CMOs, líderes de marketing e founders de empresas digitais.',
  offer: 'Diagnóstico gratuito da operação de conteúdo', channels: ['instagram', 'linkedin', 'youtube'],
  importantDates: '05/08 anúncio; 12/08 demonstração; 26/08 fechamento',
  funnel: 'Descoberta → Educação → Prova → Conversão',
  ctas: ['Solicitar diagnóstico', 'Ver demonstração'],
  executionPlan: ['Publicar manifesto', 'Distribuir série educativa', 'Apresentar estudo de caso', 'Ativar retargeting', 'Consolidar aprendizados'],
  status: 'active', brainRevision: 3, createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-02T12:30:00.000Z',
}];

const initialAssets: LibraryAsset[] = [
  { id: 'asset-guide', workspaceId: activeWorkspace.id, title: 'Guia de tom de voz', type: 'document', tags: ['brain', 'marca'], createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-01T09:00:00.000Z' },
  { id: 'asset-template', workspaceId: activeWorkspace.id, title: 'Template carrossel — Educação', type: 'template', tags: ['instagram', 'carrossel'], createdAt: '2026-08-01T11:00:00.000Z', updatedAt: '2026-08-01T11:00:00.000Z' },
];

const defaultState: OperationsState = {
  brain: initialBrain,
  campaigns: initialCampaigns,
  assets: initialAssets,
  posts: INITIAL_POSTS.map((post, index) => ({
    ...post,
    campaignId: index < 3 ? 'strategy-q3' : undefined,
    strategyId: index < 3 ? 'strategy-q3' : undefined,
    brainRevision: index < 3 ? 3 : undefined,
    origin: index < 3 ? 'strategy' : 'manual',
    versions: [{ id: `${post.id}-v1`, number: 1, label: 'Versão inicial', author: post.author, createdAt: post.createdAt, copy: post.copy }],
  })),
  activeCampaignId: 'strategy-q3',
};

const OperationsContext = React.createContext<OperationsContextValue | null>(null);

function loadState(): OperationsState {
  try {
    const stored = window.localStorage.getItem(storageKey);
    return stored ? { ...defaultState, ...JSON.parse(stored) } : defaultState;
  } catch {
    return defaultState;
  }
}

export function OperationsProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = React.useState<OperationsState>(loadState);

  React.useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(state));
  }, [state]);

  const updateBrain = React.useCallback((values: Partial<BrandBrain>) => {
    setState((current) => ({ ...current, brain: { ...current.brain, ...values, revision: current.brain.revision + 1, updatedAt: now() } }));
  }, []);

  const addBrainSource = React.useCallback((source: BrandBrain['sourceFiles'][number]) => {
    setState((current) => ({ ...current, brain: { ...current.brain, sourceFiles: [source, ...current.brain.sourceFiles], revision: current.brain.revision + 1, updatedAt: now() } }));
  }, []);

  const createCampaign = React.useCallback((values: Omit<StrategyCampaign, 'id' | 'workspaceId' | 'brainRevision' | 'createdAt' | 'updatedAt'>) => {
    const timestamp = now();
    const campaign: StrategyCampaign = { ...values, id: `strategy-${Date.now()}`, workspaceId: activeWorkspace.id, brainRevision: state.brain.revision, createdAt: timestamp, updatedAt: timestamp };
    setState((current) => ({ ...current, campaigns: [campaign, ...current.campaigns], activeCampaignId: campaign.id }));
    return campaign;
  }, [state.brain.revision]);

  const updateCampaign = React.useCallback((id: string, values: Partial<StrategyCampaign>) => {
    setState((current) => ({ ...current, campaigns: current.campaigns.map((campaign) => campaign.id === id ? { ...campaign, ...values, updatedAt: now() } : campaign) }));
  }, []);

  const setActiveCampaignId = React.useCallback((id?: string) => setState((current) => ({ ...current, activeCampaignId: id })), []);
  const addPosts = React.useCallback((posts: Post[]) => setState((current) => ({ ...current, posts: [...posts, ...current.posts] })), []);
  const updatePosts: React.Dispatch<React.SetStateAction<Post[]>> = React.useCallback((value) => {
    setState((current) => ({ ...current, posts: typeof value === 'function' ? value(current.posts) : value }));
  }, []);

  const addAsset = React.useCallback((values: Omit<LibraryAsset, 'id' | 'workspaceId' | 'createdAt' | 'updatedAt'>) => {
    const timestamp = now();
    const asset: LibraryAsset = { ...values, id: `asset-${Date.now()}`, workspaceId: activeWorkspace.id, createdAt: timestamp, updatedAt: timestamp };
    setState((current) => ({ ...current, assets: [asset, ...current.assets] }));
    return asset;
  }, []);

  const requiredBrainFields: Array<keyof BrandBrain> = ['company', 'products', 'services', 'visualIdentity', 'toneOfVoice', 'audience', 'personas', 'objectives', 'differentiators', 'competitors', 'objections', 'pains', 'desires', 'faq'];
  const brainCompleteness = Math.round(requiredBrainFields.filter((field) => String(state.brain[field] || '').trim()).length / requiredBrainFields.length * 100);
  const activeCampaign = state.campaigns.find((campaign) => campaign.id === state.activeCampaignId);

  return <OperationsContext.Provider value={{ ...state, activeWorkspace, activeCampaign, brainCompleteness, updateBrain, addBrainSource, createCampaign, updateCampaign, setActiveCampaignId, addPosts, updatePosts, addAsset }}>{children}</OperationsContext.Provider>;
}

export function useOperations() {
  const value = React.useContext(OperationsContext);
  if (!value) throw new Error('useOperations deve ser usado dentro de OperationsProvider.');
  return value;
}
