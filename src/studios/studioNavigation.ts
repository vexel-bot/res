import type { NavigationTab } from '../types';

export type StudioModule = 'create-image' | 'create-video';
export type StudioCategory = 'image' | 'video' | 'advertising' | 'tools';
export const studioTools = [
  { id: 'image-generate', category: 'image', label: 'Gerar Imagem', path: '/studios/image/generate', module: 'create-image', entry: 'create' },
  { id: 'image-edit', category: 'image', label: 'Editar Imagem', path: '/studios/image/edit', module: 'create-image', entry: 'edit' },
  { id: 'video-create', category: 'video', label: 'Criar Vídeo', path: '/studios/video/create', module: 'create-video', entry: 'ai' },
  { id: 'video-edit', category: 'video', label: 'Editar Vídeo', path: '/studios/video/edit', module: 'create-video', entry: 'editor' },
  { id: 'video-motion', category: 'video', label: 'Motion Design', path: '/studios/video/motion', module: 'create-video', entry: 'motion' },
  { id: 'ad-create', category: 'advertising', label: 'Criar Anúncio', path: '/studios/advertising/create', module: 'create-video', entry: 'ad' },
  { id: 'ad-creatives', category: 'advertising', label: 'Criativos para Anúncios', path: '/studios/advertising/creatives', module: 'create-image', entry: 'advertising' },
  { id: 'image-composition', category: 'tools', label: 'Composição e formatos', path: '/studios/tools/composition', module: 'create-image', entry: 'composition' },
  { id: 'image-editorial', category: 'tools', label: 'Produção editorial e carrosséis', path: '/studios/tools/editorial', module: 'create-image', entry: 'editorial' },
] as const;
export type StudioTool = typeof studioTools[number];
export type StudioToolId = StudioTool['id'];
export const studioCategories: Array<{ id: StudioCategory; label: string }> = [
  { id: 'image', label: 'Imagem' }, { id: 'video', label: 'Vídeo' },
  { id: 'advertising', label: 'Publicidade' }, { id: 'tools', label: 'Ferramentas adicionais' },
];
export const studioTool = (id: StudioToolId) => studioTools.find(tool => tool.id === id)!;
export const isStudioModule = (tab: NavigationTab): tab is StudioModule => tab === 'create-image' || tab === 'create-video';
export const defaultStudioTool = (module: StudioModule) => studioTool(module === 'create-video' ? 'video-create' : 'image-generate');
export function studioToolForPath(pathname: string): StudioTool | undefined {
  const path = pathname.replace(/\/+$/, '') || '/';
  if (path === '/studios' || path === '/image') return defaultStudioTool('create-image');
  if (path === '/video') return defaultStudioTool('create-video');
  return studioTools.find(tool => tool.path === path);
}
export const permittedStudioTools = (canAccess: (module: StudioModule) => boolean) => studioTools.filter(tool => canAccess(tool.module));

export function categoryStudioTool(tools: readonly StudioTool[], category: StudioCategory, preferredId?: StudioToolId) {
  return tools.find(tool => tool.category === category && tool.id === preferredId) || tools.find(tool => tool.category === category);
}
export const futureStudioTools: Partial<Record<StudioCategory, readonly string[]>> = {
  advertising: ['Variações de Criativos'],
  tools: ['Variações de imagem e vídeo', 'Adaptação para redes sociais'],
};

/** Internal module identities remain unchanged: Studios is navigation, not a new entitlement. */
export function studioNavigationAllowed() {
  return window.dispatchEvent(new Event('clicko:studio-before-leave', { cancelable: true }));
}
