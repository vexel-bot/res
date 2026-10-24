import type { ChatAttachmentInput } from './conversation';

/** Read a validated chat attachment without changing its name, MIME type or bytes. */
export const fileToAttachment = (file: File) => new Promise<ChatAttachmentInput>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve({ name: file.name, type: file.type || 'application/octet-stream', size: file.size, dataUrl: String(reader.result || '') });
  reader.onerror = () => reject(reader.error);
  reader.readAsDataURL(file);
});
