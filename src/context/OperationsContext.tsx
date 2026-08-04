import React from 'react';
import { INITIAL_POSTS, INITIAL_WORKSPACES } from '../data/mockData';
import type { BrandBrain, LibraryAsset, Post, StrategyCampaign, Workspace } from '../types';
import { useGovernance } from './GovernanceContext';

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

const now = () => new Date().toISOString();

function createInitialBrain(ws: Workspace): BrandBrain {
  const isPersonal = ws.id === 'ws-personal';
  return {
    workspaceId: ws.id,
    revision: 3,
    updatedAt: '2026-08-02T12:30:00.000Z',
    company: isPersonal
      ? 'Pedro Henrique é Tech Lead, criador de conteúdo e especialista em engenharia de IA e liderança de produto.'
      : 'Clicko Studio é uma plataforma de operação de mídia com inteligência artificial para marcas e equipes de marketing.',
    products: isPersonal
      ? 'Conteúdo técnico, newsletters sobre IA, mentorias de engenharia e projetos open-source.'
      : 'Clicko Studio — planejamento, produção, aprovação, publicação e análise de mídia em um único fluxo.',
    services: isPersonal
      ? 'Artigos autorais, vlogs de engenharia, palestras sobre IA e consultoria de arquitetura de software.'
      : 'Estratégia de conteúdo, automação editorial, criação multimídia, governança e inteligência de desempenho.',
    visualIdentity: isPersonal
      ? 'Estética pessoal, moderna e autêntica. Verdes, cinzas e alto contraste com fotos reais do ambiente de desenvolvimento.'
      : 'Visual premium e tecnológico. Preto, branco, cinzas e verde sutil. Alto contraste, composições limpas e sem efeitos excessivos.',
    toneOfVoice: ws.brandProfile.tone,
    audience: ws.brandProfile.targetAudience,
    personas: isPersonal
      ? 'Desenvolvedores em transição para liderança, criadores em tech e profissionais buscando produtividade com IA.'
      : 'Líder de marketing orientado a resultado; social media que precisa ganhar escala; fundador que quer consistência de marca.',
    objectives: isPersonal
      ? 'Construir autoridade técnica, compartilhar conhecimento prático e expandir a comunidade de desenvolvedores.'
      : 'Aumentar autoridade, gerar demanda qualificada e tornar a operação de mídia previsível e mensurável.',
    differentiators: isPersonal
      ? 'Experiência real como Tech Lead, abordagem "build in public" e didática prática sem enrolação.'
      : 'Memória estratégica persistente, criação multimodal e rastreabilidade completa da estratégia ao resultado.',
    competitors: isPersonal
      ? 'Criadores genéricos de tecnologia sem experiência de produção de software em escala.'
      : 'Suites de social media, ferramentas isoladas de IA generativa e plataformas de automação sem contexto de marca.',
    objections: isPersonal
      ? 'Falta de tempo na rotina corporativa e equilíbrio entre conteúdo autoral e liderança técnica.'
      : 'Tempo de implantação, consistência das respostas de IA, governança e clareza sobre retorno do investimento.',
    pains: isPersonal
      ? 'Dificuldade de conciliar produção de conteúdo com a gestão de equipes de engenharia.'
      : 'Ferramentas fragmentadas, briefing incompleto, retrabalho, demora em aprovações e dificuldade de atribuição.',
    desires: isPersonal
      ? 'Impactar milhares de desenvolvedores, criar projetos autorais relevantes e liderar conversas sobre IA.'
      : 'Produzir mais com qualidade, manter a marca consistente e transformar dados em próximas ações.',
    faq: isPersonal
      ? 'Qual o foco dos posts? Práticas de engenharia, IA generativa e liderança técnica em 2026.'
      : 'Como o Brain é usado? Toda geração consulta a revisão ativa.\nComo funciona aprovação? Conteúdos mantêm comentários, histórico e versões.',
    requiredWords: isPersonal ? 'Pedro Henrique; Tech Lead; Inteligência Artificial; Engenharia' : 'Clicko Studio; operação de mídia; inteligência estratégica',
    forbiddenWords: 'promessas garantidas; linguagem sensacionalista; jargão sem explicação',
    history: isPersonal ? 'Iniciado como dev log pessoal e transformado em canal de referência em IA e liderança.' : 'Projeto iniciado como gerador de conteúdo e evoluído para sistema operacional de mídia com IA.',
    sourceLinks: isPersonal ? ['https://github.com/vexel-bot', 'https://linkedin.com/in/pedro-henrique-tech'] : ['https://clickostudio.com/'],
    sourceFiles: isPersonal
      ? [
          { id: 'personal-avatar', name: 'Foto de Perfil HD.jpg', type: 'image', addedAt: '2026-08-01T10:00:00.000Z' },
          { id: 'personal-bio', name: 'Bio & Linhas Editoriais 2026.pdf', type: 'document', addedAt: '2026-08-01T10:15:00.000Z' },
        ]
      : [
          { id: 'brain-logo', name: 'Identidade oficial Clicko', type: 'logo', addedAt: '2026-08-02T10:00:00.000Z' },
          { id: 'brain-guide', name: 'Guia de tom de voz.pdf', type: 'document', addedAt: '2026-08-02T10:15:00.000Z' },
        ],
  };
}

function createInitialCampaigns(ws: Workspace): StrategyCampaign[] {
  const isPersonal = ws.id === 'ws-personal';
  if (isPersonal) {
    return [{
      id: 'strategy-personal-q3', workspaceId: ws.id, name: 'Branding Pessoal & IA 2026',
      objective: 'Fortalecer posicionamento como referência em liderança de engenharia e aplicação de IA.',
      startDate: '2026-08-01', endDate: '2026-08-31', budget: 'R$ 2.500',
      kpis: ['Engajamento autoral', 'Alcance orgânico', 'Conexões no LinkedIn', 'Inscritos no YouTube'],
      products: 'Conteúdo autoral e didático', audience: 'Desenvolvedores, Tech Leads, Engineering Managers e entusiastas de IA.',
      offer: 'Guia de Produtividade com Agentes de IA', channels: ['linkedin', 'instagram', 'youtube'],
      importantDates: '02/08 artigo publicado; 04/08 carrossel setup; 05/08 vlog youtube',
      funnel: 'Atração → Conexão Autêntica → Valor Prático → Comunidade',
      ctas: ['Acompanhar no LinkedIn', 'Inscrever-se no canal'],
      executionPlan: ['Postar lições de liderança', 'Lançar vlog de setup dev', 'Demonstrar fluxo de código com agentes', 'Fazer live Q&A'],
      status: 'active', brainRevision: 3, createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-02T12:30:00.000Z',
    }];
  }

  return [{
    id: 'strategy-q3', workspaceId: ws.id, name: 'Lançamento Clicko Q3',
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
}

function createInitialAssets(ws: Workspace): LibraryAsset[] {
  const isPersonal = ws.id === 'ws-personal';
  if (isPersonal) {
    return [
      { id: 'asset-p-avatar', workspaceId: ws.id, title: 'Foto de Perfil Oficial', type: 'image', tags: ['pessoal', 'avatar'], createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-01T09:00:00.000Z' },
      { id: 'asset-p-template', workspaceId: ws.id, title: 'Template Carrossel Dev', type: 'template', tags: ['linkedin', 'dev'], createdAt: '2026-08-01T11:00:00.000Z', updatedAt: '2026-08-01T11:00:00.000Z' },
    ];
  }

  return [
    { id: 'asset-guide', workspaceId: ws.id, title: 'Guia de tom de voz', type: 'document', tags: ['brain', 'marca'], createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-01T09:00:00.000Z' },
    { id: 'asset-template', workspaceId: ws.id, title: 'Modelo de carrossel — Educação', type: 'template', tags: ['instagram', 'carrossel'], createdAt: '2026-08-01T11:00:00.000Z', updatedAt: '2026-08-01T11:00:00.000Z' },
  ];
}

function getDefaultState(ws: Workspace): OperationsState {
  const isPersonal = ws.id === 'ws-personal';
  const campaigns = createInitialCampaigns(ws);
  const activeCampId = campaigns[0]?.id;
  const filteredPosts = INITIAL_POSTS.filter((post) => isPersonal ? post.workspaceId === 'ws-personal' : post.workspaceId !== 'ws-personal').map((post, index) => ({
    ...post,
    campaignId: index < 3 ? activeCampId : undefined,
    strategyId: index < 3 ? activeCampId : undefined,
    brainRevision: index < 3 ? 3 : undefined,
    origin: index < 3 ? ('strategy' as const) : ('manual' as const),
    versions: [{ id: `${post.id}-v1`, number: 1, label: 'Versão inicial', author: post.author, createdAt: post.createdAt, copy: post.copy }],
  }));

  return {
    brain: createInitialBrain(ws),
    campaigns,
    assets: createInitialAssets(ws),
    posts: filteredPosts,
    activeCampaignId: activeCampId,
  };
}

const OperationsContext = React.createContext<OperationsContextValue | null>(null);

function loadStateForWorkspace(ws: Workspace): OperationsState {
  const storageKey = `clicko:operations:${ws.id}`;
  const defaultState = getDefaultState(ws);
  try {
    const stored = window.localStorage.getItem(storageKey);
    return stored ? { ...defaultState, ...JSON.parse(stored) } : defaultState;
  } catch {
    return defaultState;
  }
}

export function OperationsProvider({ children }: { children: React.ReactNode }) {
  const governance = useGovernance();
  const environmentMode = governance.environmentMode;

  const activeWorkspace = React.useMemo(() => {
    return INITIAL_WORKSPACES.find((ws) => ws.id === (environmentMode === 'personal' ? 'ws-personal' : 'ws-1')) || INITIAL_WORKSPACES[0];
  }, [environmentMode]);

  const [state, setState] = React.useState<OperationsState>(() => loadStateForWorkspace(activeWorkspace));

  React.useEffect(() => {
    setState(loadStateForWorkspace(activeWorkspace));
  }, [activeWorkspace]);

  React.useEffect(() => {
    const storageKey = `clicko:operations:${activeWorkspace.id}`;
    window.localStorage.setItem(storageKey, JSON.stringify(state));
  }, [state, activeWorkspace.id]);

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
  }, [state.brain.revision, activeWorkspace.id]);

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
  }, [activeWorkspace.id]);

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
