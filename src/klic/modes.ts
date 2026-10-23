export type KlicModeId = 'create' | 'strategy' | 'research' | 'analyze' | 'ideas' | 'post' | 'image' | 'video' | 'local-production';

export const klicModes: Array<{ id: KlicModeId; label: string; actionId: string }> = [
  { id: 'create', label: 'Criar', actionId: 'create.general' },
  { id: 'strategy', label: 'Estratégia', actionId: 'mode.strategist' },
  { id: 'research', label: 'Pesquisar', actionId: 'mode.explorer' },
  { id: 'analyze', label: 'Analisar', actionId: 'mode.diagnostic' },
  { id: 'ideas', label: 'Ideias', actionId: 'create.ideas' },
  { id: 'post', label: 'Post', actionId: 'create.post' },
  { id: 'image', label: 'Imagem', actionId: 'create.image' },
  { id: 'video', label: 'Vídeo', actionId: 'create.video' },
  { id: 'local-production', label: 'Produção local', actionId: 'mode.local-production' },
];
