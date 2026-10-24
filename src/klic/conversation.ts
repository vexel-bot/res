export const ATTACHMENT_LIMITS = { count: 4, bytes: 6 * 1024 * 1024, text: 32000 };
export const FILE_TYPES: Record<string, string[]> = {
  png: ['image/png'], jpg: ['image/jpeg'], jpeg: ['image/jpeg'], webp: ['image/webp'],
  pdf: ['application/pdf'], txt: ['text/plain'], csv: ['text/csv', 'text/plain', 'application/vnd.ms-excel'],
  docx: ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  xlsx: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
  mp3: ['audio/mpeg'], wav: ['audio/wav', 'audio/x-wav'], webm: ['audio/webm'], ogg: ['audio/ogg'],
};
export const FILE_ACCEPT = Object.keys(FILE_TYPES).map(extension => '.' + extension).join(',');
export type ChatAttachmentInput = { name: string; type: string; size: number; dataUrl?: string };
export type ChatFile = { id: string; name: string; type: string; size: number; dataUrl?: string; text?: string };
export type ChatMessage = {
  localProduction?: boolean;
  production?: { documentId: string; module: 'create-image' | 'create-video'; taskId: string };
  favorite?: boolean; brandScore?: number; researchedExternally?: boolean;
  actions?: import('../types').AIChatMessage['actions'];
  id: string; role: 'user' | 'assistant'; content: string; createdAt: string; module: 'ai-chat';
  status: 'pending' | 'streaming' | 'complete' | 'error' | 'cancelled';
  requestId: string; attachments?: ChatFile[]; error?: string;
};
export type Conversation = { id: string; title: string; createdAt: string; updatedAt: string; messages: ChatMessage[] };
export function validateFile(file: { name: string; type: string; size: number }) {
  const extension = file.name.split('.').pop()?.toLowerCase() || '';
  if (!Object.hasOwn(FILE_TYPES, extension)) throw new Error('Formato de arquivo não suportado.');
  if (!file.size || file.size > ATTACHMENT_LIMITS.bytes) throw new Error('Envie arquivos não vazios de até 6 MB.');
  if (file.type && file.type !== 'application/octet-stream' && !FILE_TYPES[extension].includes(file.type.split(';')[0])) throw new Error('O tipo do arquivo não corresponde ao formato informado.');
  return { extension, mime: FILE_TYPES[extension][0] };
}
