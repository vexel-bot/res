import React from 'react';
import { INITIAL_POSTS, INITIAL_WORKSPACES } from '../data/mockData';
import type {
  AIContextSnapshot,
  AIMemoryEntry,
  ClientIntelligenceProfile,
  ConnectedAccount,
  CreativeIdea,
  LearningSignal,
  LibraryAsset,
  Post,
  StrategyCampaign,
  StudioHandoff,
  Workspace,
} from '../types';
import { useGovernance } from './GovernanceContext';

type OperationsState = {
  clients: ClientIntelligenceProfile[];
  campaigns: StrategyCampaign[];
  creativeIdeas: CreativeIdea[];
  selectedCreativeIdeaIds: string[];
  learningSignals: LearningSignal[];
  assets: LibraryAsset[];
  posts: Post[];
  activeClientId?: string;
  activeCampaignId?: string;
  studioHandoff?: StudioHandoff;
  aiMemory: AIMemoryEntry[];
  connectedAccounts: ConnectedAccount[];
};

type OperationsContextValue = OperationsState & {
  activeWorkspace: Workspace;
  activeClient?: ClientIntelligenceProfile;
  activeCampaign?: StrategyCampaign;
  contextSnapshot: AIContextSnapshot;
  contextRevision: number;
  updateClient: (id: string, values: Partial<ClientIntelligenceProfile>) => void;
  setActiveClientId: (id?: string) => void;
  createCampaign: (campaign: Omit<StrategyCampaign, 'id' | 'workspaceId' | 'contextRevision' | 'createdAt' | 'updatedAt'>) => StrategyCampaign;
  updateCampaign: (id: string, values: Partial<StrategyCampaign>) => void;
  setActiveCampaignId: (id?: string) => void;
  addPosts: (posts: Post[]) => void;
  updatePosts: React.Dispatch<React.SetStateAction<Post[]>>;
  addAsset: (asset: Omit<LibraryAsset, 'id' | 'workspaceId' | 'createdAt' | 'updatedAt'>) => LibraryAsset;
  setCreativeIdeas: (ideas: CreativeIdea[]) => void;
  toggleCreativeIdea: (id: string) => void;
  prepareStudioHandoff: (handoff: Omit<StudioHandoff, 'id' | 'createdAt'>) => StudioHandoff;
  clearStudioHandoff: () => void;
  createRepurposeHandoff: (post: Post, format: StudioHandoff['format']) => StudioHandoff;
  addLearningSignal: (signal: Omit<LearningSignal, 'id' | 'createdAt'>) => LearningSignal;
  upsertAIMemory: (memory: Omit<AIMemoryEntry, 'id' | 'workspaceId' | 'createdAt' | 'updatedAt' | 'occurrences'> & { id?: string }) => AIMemoryEntry;
  updateAIMemory: (id: string, values: Partial<Pick<AIMemoryEntry, 'label' | 'value' | 'scope' | 'category'>>) => void;
  deleteAIMemory: (id: string) => void;
  addConnectedAccount: (platform: ConnectedAccount['platform']) => ConnectedAccount;
  updateConnectedAccount: (id: string, values: Partial<ConnectedAccount>) => void;
  removeConnectedAccount: (id: string) => void;
};

const now = () => new Date().toISOString();

function createInitialContextSeed(ws: Workspace): AIContextSnapshot {
  const isPersonal = ws.id === 'ws-personal';
  const isSeedCompany = ws.id === 'ws-1';
  if (!isPersonal && !isSeedCompany) {
    return {
      workspaceId: ws.id, revision: 1, company: ws.name,
      products: '', services: '', visualIdentity: '', toneOfVoice: ws.brandProfile.tone || '',
      audience: ws.brandProfile.targetAudience || '', personas: '', objectives: '', differentiators: '',
      competitors: '', objections: '', pains: '', desires: '', faq: '', requiredWords: '', forbiddenWords: '',
      history: '',
    };
  }
  return {
    workspaceId: ws.id,
    revision: 3,
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
      : 'Como a memória é usada? A KLIC seleciona apenas o contexto relevante para cada pedido.\nComo funciona aprovação? Conteúdos mantêm comentários, histórico e versões.',
    requiredWords: isPersonal ? 'Pedro Henrique; Tech Lead; Inteligência Artificial; Engenharia' : 'Clicko Studio; operação de mídia; inteligência estratégica',
    forbiddenWords: 'promessas garantidas; linguagem sensacionalista; jargão sem explicação',
    history: isPersonal ? 'Iniciado como dev log pessoal e transformado em canal de referência em IA e liderança.' : 'Projeto iniciado como gerador de conteúdo e evoluído para sistema operacional de mídia com IA.',
  };
}

function createInitialClients(ws: Workspace, context: AIContextSnapshot): ClientIntelligenceProfile[] {
  const timestamp = '2026-08-02T12:30:00.000Z';
  if (ws.id === 'ws-personal') {
    return [{
      id: 'client-personal', workspaceId: ws.id, name: ws.name, segment: 'Marca pessoal e tecnologia',
      products: context.products, audience: context.audience, positioning: context.objectives,
      toneOfVoice: context.toneOfVoice, visualIdentity: context.visualIdentity, differentiators: context.differentiators,
      featuredOffer: 'Guia de Produtividade com Agentes de IA', currentObjective: context.objectives,
      highlightedContentIds: [], activeCampaignIds: ['strategy-personal-q3'],
      recommendedActions: ['Consolidar a série sobre agentes de IA', 'Transformar o vlog em três cortes curtos', 'Distribuir o artigo no LinkedIn'],
      updatedAt: timestamp,
    }];
  }

  if (ws.id !== 'ws-1') {
    return [{
      id: `client-${ws.id}`, workspaceId: ws.id, name: ws.name, segment: ws.brandProfile.industry || '',
      products: '', audience: ws.brandProfile.targetAudience || '', positioning: '', toneOfVoice: ws.brandProfile.tone || '',
      visualIdentity: '', differentiators: '', featuredOffer: '', currentObjective: '', highlightedContentIds: [],
      activeCampaignIds: [], recommendedActions: ['Conversar com a KLIC sobre o projeto', 'Definir o primeiro objetivo', 'Criar o primeiro conteúdo'], updatedAt: now(),
    }];
  }

  return [
    {
      id: 'client-clicko', workspaceId: ws.id, name: 'Clicko Studio', segment: 'Software para operações de social media',
      products: context.products, audience: context.audience, positioning: 'Sistema operacional de social media com contexto persistente.',
      toneOfVoice: context.toneOfVoice, visualIdentity: context.visualIdentity, differentiators: context.differentiators,
      featuredOffer: 'Diagnóstico gratuito da operação de conteúdo', currentObjective: 'Gerar demanda qualificada para o lançamento Q3.',
      highlightedContentIds: [], activeCampaignIds: ['strategy-q3'],
      recommendedActions: ['Validar a mensagem central do lançamento', 'Produzir a peça de descoberta', 'Preparar a sequência de prova para aprovação'],
      updatedAt: timestamp,
    },
    {
      id: 'client-vitalis', workspaceId: ws.id, name: 'Clínica Vitalis', segment: 'Saúde e bem-estar',
      products: 'Consultas preventivas e programas de bem-estar', audience: 'Adultos que buscam prevenção com atendimento humanizado.',
      positioning: 'Cuidado preventivo acessível, confiável e próximo.', toneOfVoice: 'Acolhedor, claro e responsável.',
      visualIdentity: 'Fotografia humana, composição limpa e contraste suave.', differentiators: 'Atendimento integrado e acompanhamento próximo.',
      featuredOffer: 'Programa Vitalis Preventivo', currentObjective: 'Aumentar agendamentos qualificados sem apelos sensacionalistas.',
      highlightedContentIds: [], activeCampaignIds: [],
      recommendedActions: ['Estruturar campanha educativa', 'Mapear objeções sobre prevenção', 'Criar uma sequência de perguntas frequentes'],
      updatedAt: timestamp,
    },
  ];
}

function createInitialLearningSignals(clientId: string): LearningSignal[] {
  return [{
    id: 'learning-hook-clarity', clientId,
    label: 'Hipótese de mensagem',
    evidence: 'Leitura baseada apenas nos metadados e padrões dos conteúdos salvos localmente.',
    recommendation: 'Priorizar hooks diretos que apresentem o problema antes da solução.',
    confidence: 'hypothesis', source: 'content-metadata', createdAt: '2026-08-02T12:30:00.000Z',
  }];
}

function createInitialAIMemory(ws: Workspace, context: AIContextSnapshot): AIMemoryEntry[] {
  const createdAt = '2026-08-02T12:30:00.000Z';
  const base: Array<Pick<AIMemoryEntry, 'category' | 'label' | 'value'>> = [
    { category: 'identity', label: 'Identidade e posicionamento', value: context.company },
    { category: 'identity', label: 'Público principal', value: context.audience },
    { category: 'communication', label: 'Tom de voz', value: context.toneOfVoice },
    { category: 'communication', label: 'Expressões a evitar', value: context.forbiddenWords },
    { category: 'content', label: 'Objetivo recorrente', value: context.objectives },
    { category: 'visual', label: 'Preferência visual', value: context.visualIdentity },
  ];
  return base.filter((entry) => entry.value.trim()).map((entry, index) => ({ id: `memory-${ws.id}-${index}`, workspaceId: ws.id, ...entry, scope: 'permanent', confidence: 100, source: 'conversation', occurrences: 1, createdAt, updatedAt: createdAt }));
}

function contextRevisionFor(memory: AIMemoryEntry[]) {
  return Math.max(1, memory.reduce((total, entry) => total + entry.occurrences, 0));
}

function buildContextSnapshot(ws: Workspace, memory: AIMemoryEntry[], client?: ClientIntelligenceProfile): AIContextSnapshot {
  const durable = memory.filter((entry) => entry.scope === 'recurring' || entry.scope === 'permanent');
  const find = (patterns: RegExp[], category?: AIMemoryEntry['category']) => durable.find((entry) => (!category || entry.category === category) && patterns.some((pattern) => pattern.test(`${entry.label} ${entry.value}`.toLowerCase())))?.value || '';
  const identity = durable.filter((entry) => entry.category === 'identity').map((entry) => entry.value).join('\n');
  return {
    workspaceId: ws.id,
    revision: contextRevisionFor(durable),
    company: find([/identidade/, /empresa/, /posicionamento/], 'identity') || identity || ws.name,
    products: find([/produto/, /oferta/], 'content') || client?.products || '',
    services: find([/serviço/, /entrega/], 'content') || '',
    visualIdentity: find([/visual/, /estética/, /cor/], 'visual') || client?.visualIdentity || '',
    toneOfVoice: find([/tom de voz/, /comunicação/, /linguagem/], 'communication') || client?.toneOfVoice || ws.brandProfile.tone || '',
    audience: find([/público/, /audiência/, /persona/], 'identity') || client?.audience || ws.brandProfile.targetAudience || '',
    personas: find([/persona/], 'identity'),
    objectives: find([/objetivo/, /meta/, /prioridade/], 'content') || client?.currentObjective || '',
    differentiators: find([/diferencial/, /posicionamento/], 'identity') || client?.differentiators || '',
    competitors: find([/concorrent/], 'identity'),
    objections: find([/objeção/], 'content'),
    pains: find([/dor/, /problema/], 'content'),
    desires: find([/desejo/, /transformação/], 'content'),
    faq: find([/faq/, /pergunta recorrente/], 'content'),
    requiredWords: find([/palavra obrigatória/, /termo obrigatório/], 'communication'),
    forbiddenWords: find([/evitar/, /proibida/, /não usar/], 'communication'),
    history: durable.map((entry) => `${entry.label}: ${entry.value}`).join('\n'),
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
      status: 'active', contextRevision: 6, createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-02T12:30:00.000Z',
    }];
  }

  if (ws.id !== 'ws-1') return [];

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
    status: 'active', contextRevision: 6, createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-02T12:30:00.000Z',
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

  if (ws.id !== 'ws-1') return [];

  return [
    { id: 'asset-guide', workspaceId: ws.id, title: 'Guia de tom de voz', type: 'document', tags: ['referência', 'marca'], createdAt: '2026-08-01T09:00:00.000Z', updatedAt: '2026-08-01T09:00:00.000Z' },
    { id: 'asset-template', workspaceId: ws.id, title: 'Modelo de carrossel — Educação', type: 'template', tags: ['instagram', 'carrossel'], createdAt: '2026-08-01T11:00:00.000Z', updatedAt: '2026-08-01T11:00:00.000Z' },
  ];
}

function createInitialConnectedAccounts(ws: Workspace): ConnectedAccount[] {
  const platforms: ConnectedAccount['platform'][] = ws.id === 'ws-personal' ? ['instagram', 'youtube'] : ['instagram', 'linkedin', 'tiktok'];
  return platforms.map((platform, index) => ({
    id: `social-${ws.id}-${platform}`,
    workspaceId: ws.id,
    platform,
    handle: 'Autorização pendente',
    connected: false,
    followers: '—',
    bestTime: 'Sem dados',
    engagement: '—',
    name: platform.charAt(0).toUpperCase() + platform.slice(1),
    company: ws.name,
    lastSync: 'Nunca',
    permissions: [],
    isDefault: index === 0,
    connectionStatus: 'not_configured',
    lastError: 'Credenciais OAuth não configuradas para este ambiente.',
  }));
}

function getDefaultState(ws: Workspace): OperationsState {
  const isPersonal = ws.id === 'ws-personal';
  const contextSeed = createInitialContextSeed(ws);
  const clients = createInitialClients(ws, contextSeed);
  const campaigns = createInitialCampaigns(ws);
  const activeCampId = campaigns[0]?.id;
  const filteredPosts = (ws.id === 'ws-1' ? INITIAL_POSTS.filter((post) => post.workspaceId !== 'ws-personal') : isPersonal ? INITIAL_POSTS.filter((post) => post.workspaceId === 'ws-personal') : []).map((post, index) => ({
    ...post,
    workspaceId: ws.id,
    campaignId: index < 3 ? activeCampId : undefined,
    strategyId: index < 3 ? activeCampId : undefined,
    contextRevision: index < 3 ? 6 : undefined,
    origin: index < 3 ? ('strategy' as const) : ('manual' as const),
    versions: [{ id: `${post.id}-v1`, number: 1, label: 'Versão inicial', author: post.author, createdAt: post.createdAt, copy: post.copy }],
  }));

  return {
    clients,
    campaigns,
    creativeIdeas: [],
    selectedCreativeIdeaIds: [],
    learningSignals: ws.id === 'ws-1' || isPersonal ? createInitialLearningSignals(clients[0].id) : [],
    aiMemory: createInitialAIMemory(ws, contextSeed),
    connectedAccounts: createInitialConnectedAccounts(ws),
    assets: createInitialAssets(ws),
    posts: filteredPosts,
    activeClientId: clients[0].id,
    activeCampaignId: activeCampId,
  };
}

const OperationsContext = React.createContext<OperationsContextValue | null>(null);

function loadStateForWorkspace(ws: Workspace): OperationsState {
  const storageKey = `clicko:operations:${ws.id}`;
  const defaultState = getDefaultState(ws);
  try {
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) return defaultState;
    const parsed = JSON.parse(stored) as Partial<OperationsState>;
    return {
      ...defaultState,
      clients: parsed.clients || defaultState.clients,
      campaigns: parsed.campaigns || defaultState.campaigns,
      creativeIdeas: parsed.creativeIdeas || defaultState.creativeIdeas,
      selectedCreativeIdeaIds: parsed.selectedCreativeIdeaIds || defaultState.selectedCreativeIdeaIds,
      learningSignals: parsed.learningSignals || defaultState.learningSignals,
      assets: parsed.assets || defaultState.assets,
      posts: parsed.posts || defaultState.posts,
      activeClientId: parsed.activeClientId || defaultState.activeClientId,
      activeCampaignId: parsed.activeCampaignId || defaultState.activeCampaignId,
      studioHandoff: parsed.studioHandoff,
      aiMemory: (parsed.aiMemory || defaultState.aiMemory)
        .filter((entry) => entry.workspaceId === ws.id)
        .map((entry) => ({
          ...entry,
          source: (['conversation', 'user', 'approval', 'analytics', 'manual'] as string[]).includes(entry.source) ? entry.source : 'conversation',
          label: entry.label === 'Marca e posicionamento' ? 'Identidade e posicionamento' : entry.label === 'Objetivo de conteúdo' ? 'Objetivo recorrente' : entry.label === 'Identidade visual' ? 'Preferência visual' : entry.label,
        })),
      connectedAccounts: (parsed.connectedAccounts || defaultState.connectedAccounts)
        .filter((account) => !account.workspaceId || account.workspaceId === ws.id)
        .map((account) => ({ ...account, workspaceId: ws.id })),
    };
  } catch {
    return defaultState;
  }
}

export function OperationsProvider({ children }: { children: React.ReactNode }) {
  const governance = useGovernance();
  const environmentMode = governance.environmentMode;
  const activeAccount = governance.activeAccount;

  const activeWorkspace = React.useMemo(() => {
    const known = INITIAL_WORKSPACES.find((ws) => ws.id === activeAccount.workspaceId);
    if (known) return known;
    return {
      id: activeAccount.workspaceId,
      name: activeAccount.name,
      avatar: activeAccount.avatar || '',
      plan: activeAccount.planName || (environmentMode === 'personal' ? 'Solo Creator' : 'Team'),
      membersCount: activeAccount.membersCount || 1,
      brandProfile: {
        name: activeAccount.name,
        industry: environmentMode === 'personal' ? 'Marca pessoal / Creator' : '',
        tone: '', targetAudience: '', keywords: [], doAndDonts: '', primaryColor: '#8bd132',
      },
    };
  }, [activeAccount, environmentMode]);

  const [state, setState] = React.useState<OperationsState>(() => loadStateForWorkspace(activeWorkspace));
  const loadedWorkspaceId = React.useRef(activeWorkspace.id);

  React.useEffect(() => {
    if (loadedWorkspaceId.current !== activeWorkspace.id) {
      loadedWorkspaceId.current = activeWorkspace.id;
      setState(loadStateForWorkspace(activeWorkspace));
      return;
    }
    const storageKey = `clicko:operations:${activeWorkspace.id}`;
    window.localStorage.setItem(storageKey, JSON.stringify(state));
  }, [state, activeWorkspace]);

  const updateClient = React.useCallback((id: string, values: Partial<ClientIntelligenceProfile>) => {
    setState((current) => ({
      ...current,
      clients: current.clients.map((client) => client.id === id ? { ...client, ...values, updatedAt: now() } : client),
    }));
  }, []);

  const setActiveClientId = React.useCallback((id?: string) => {
    setState((current) => {
      const client = current.clients.find((item) => item.id === id);
      const matchingCampaign = current.campaigns.find((campaign) => campaign.clientId === id || client?.activeCampaignIds.includes(campaign.id));
      return { ...current, activeClientId: id, activeCampaignId: matchingCampaign?.id || current.activeCampaignId };
    });
  }, []);

  const createCampaign = React.useCallback((values: Omit<StrategyCampaign, 'id' | 'workspaceId' | 'contextRevision' | 'createdAt' | 'updatedAt'>) => {
    const timestamp = now();
    const campaign: StrategyCampaign = { ...values, clientId: values.clientId || state.activeClientId, id: `strategy-${Date.now()}`, workspaceId: activeWorkspace.id, contextRevision: contextRevisionFor(state.aiMemory), createdAt: timestamp, updatedAt: timestamp };
    setState((current) => ({
      ...current,
      campaigns: [campaign, ...current.campaigns],
      clients: current.clients.map((client) => client.id === campaign.clientId
        ? { ...client, activeCampaignIds: [...new Set([campaign.id, ...client.activeCampaignIds])], updatedAt: timestamp }
        : client),
      activeCampaignId: campaign.id,
    }));
    return campaign;
  }, [state.aiMemory, state.activeClientId, activeWorkspace.id]);

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

  const setCreativeIdeas = React.useCallback((ideas: CreativeIdea[]) => {
    setState((current) => ({ ...current, creativeIdeas: ideas, selectedCreativeIdeaIds: [] }));
  }, []);

  const toggleCreativeIdea = React.useCallback((id: string) => {
    setState((current) => ({
      ...current,
      selectedCreativeIdeaIds: current.selectedCreativeIdeaIds.includes(id)
        ? current.selectedCreativeIdeaIds.filter((ideaId) => ideaId !== id)
        : [...current.selectedCreativeIdeaIds, id],
    }));
  }, []);

  const prepareStudioHandoff = React.useCallback((values: Omit<StudioHandoff, 'id' | 'createdAt'>) => {
    const handoff: StudioHandoff = { ...values, id: `handoff-${Date.now()}`, createdAt: now() };
    setState((current) => ({
      ...current,
      studioHandoff: handoff,
      activeClientId: values.clientId || current.activeClientId,
      activeCampaignId: values.campaignId || current.activeCampaignId,
    }));
    return handoff;
  }, []);

  const clearStudioHandoff = React.useCallback(() => setState((current) => ({ ...current, studioHandoff: undefined })), []);

  const createRepurposeHandoff = React.useCallback((post: Post, format: StudioHandoff['format']) => {
    const handoff: StudioHandoff = {
      id: `repurpose-${Date.now()}`, source: 'repurpose', clientId: post.clientId,
      campaignId: post.campaignId, contentId: post.id, objective: post.objective || 'Reaproveitar conteúdo preservando a mensagem central.',
      title: `Desdobramento de ${post.title}`, angle: 'Reenquadramento para um novo formato',
      hook: post.title, cta: 'Continuar a conversa com a marca', format,
      funnelStage: 'Reaproveitamento', createdAt: now(),
    };
    setState((current) => ({ ...current, studioHandoff: handoff, activeClientId: post.clientId || current.activeClientId, activeCampaignId: post.campaignId || current.activeCampaignId }));
    return handoff;
  }, []);

  const addLearningSignal = React.useCallback((values: Omit<LearningSignal, 'id' | 'createdAt'>) => {
    const signal: LearningSignal = { ...values, id: `learning-${Date.now()}`, createdAt: now() };
    setState((current) => ({ ...current, learningSignals: [signal, ...current.learningSignals] }));
    return signal;
  }, []);

  const upsertAIMemory = React.useCallback((values: Omit<AIMemoryEntry, 'id' | 'workspaceId' | 'createdAt' | 'updatedAt' | 'occurrences'> & { id?: string }) => {
    const timestamp = now();
    let result: AIMemoryEntry | undefined;
    setState((current) => {
      const normalized = values.label.trim().toLowerCase();
      const existing = current.aiMemory.find((entry) => entry.id === values.id || (entry.category === values.category && entry.label.trim().toLowerCase() === normalized));
      if (existing) {
        const changed = existing.value !== values.value;
        result = { ...existing, ...values, id: existing.id, workspaceId: activeWorkspace.id, occurrences: existing.occurrences + 1, confidence: Math.min(100, Math.max(existing.confidence, values.confidence) + 5), scope: existing.scope === 'permanent' ? 'permanent' : existing.occurrences >= 2 ? 'recurring' : values.scope, evolution: changed ? [...(existing.evolution || []), { value: existing.value, changedAt: timestamp, source: existing.source }] : existing.evolution, updatedAt: timestamp };
        return { ...current, aiMemory: current.aiMemory.map((entry) => entry.id === existing.id ? result! : entry) };
      }
      result = { ...values, id: values.id || `memory-${Date.now()}`, workspaceId: activeWorkspace.id, occurrences: 1, createdAt: timestamp, updatedAt: timestamp };
      return { ...current, aiMemory: [result, ...current.aiMemory] };
    });
    return result!;
  }, [activeWorkspace.id]);

  const updateAIMemory = React.useCallback((id: string, values: Partial<Pick<AIMemoryEntry, 'label' | 'value' | 'scope' | 'category'>>) => setState((current) => ({ ...current, aiMemory: current.aiMemory.map((entry) => entry.id === id ? { ...entry, ...values, evolution: values.value && values.value !== entry.value ? [...(entry.evolution || []), { value: entry.value, changedAt: now(), source: entry.source }] : entry.evolution, updatedAt: now() } : entry) })), []);
  const deleteAIMemory = React.useCallback((id: string) => setState((current) => ({ ...current, aiMemory: current.aiMemory.filter((entry) => entry.id !== id) })), []);
  const addConnectedAccount = React.useCallback((platform: ConnectedAccount['platform']) => {
    const account: ConnectedAccount = {
      id: `social-${activeWorkspace.id}-${platform}-${Date.now()}`, workspaceId: activeWorkspace.id, platform,
      handle: 'Autorização pendente', connected: false, followers: '—', bestTime: 'Sem dados', engagement: '—',
      name: platform.charAt(0).toUpperCase() + platform.slice(1), company: activeWorkspace.name, lastSync: 'Nunca',
      permissions: [], connectionStatus: 'not_configured', lastError: 'Credenciais OAuth não configuradas para este ambiente.',
    };
    setState((current) => ({ ...current, connectedAccounts: [...current.connectedAccounts, account] }));
    return account;
  }, [activeWorkspace.id, activeWorkspace.name]);
  const updateConnectedAccount = React.useCallback((id: string, values: Partial<ConnectedAccount>) => setState((current) => ({ ...current, connectedAccounts: current.connectedAccounts.map((account) => account.id === id ? { ...account, ...values } : account) })), []);
  const removeConnectedAccount = React.useCallback((id: string) => setState((current) => ({ ...current, connectedAccounts: current.connectedAccounts.filter((account) => account.id !== id) })), []);

  const activeClient = state.clients.find((client) => client.id === state.activeClientId);
  const activeCampaign = state.campaigns.find((campaign) => campaign.id === state.activeCampaignId);
  const contextSnapshot = React.useMemo(() => buildContextSnapshot(activeWorkspace, state.aiMemory, activeClient), [activeClient, activeWorkspace, state.aiMemory]);
  const contextRevision = contextSnapshot.revision;

  return <OperationsContext.Provider value={{
    ...state, activeWorkspace, activeClient, activeCampaign, contextSnapshot, contextRevision,
    updateClient, setActiveClientId,
    createCampaign, updateCampaign, setActiveCampaignId,
    addPosts, updatePosts, addAsset, setCreativeIdeas, toggleCreativeIdea,
    prepareStudioHandoff, clearStudioHandoff, createRepurposeHandoff, addLearningSignal,
    upsertAIMemory, updateAIMemory, deleteAIMemory,
    addConnectedAccount, updateConnectedAccount, removeConnectedAccount,
  }}>{children}</OperationsContext.Provider>;
}

export function useOperations() {
  const value = React.useContext(OperationsContext);
  if (!value) throw new Error('useOperations deve ser usado dentro de OperationsProvider.');
  return value;
}
