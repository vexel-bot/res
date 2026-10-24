import { createHash, randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readdirSync, statSync, unlinkSync } from 'node:fs';
import path from 'node:path';
import { AtomicJsonStore } from '../atomicJsonStore';
import type { ChatMessage, Conversation } from '../../src/klic/conversation';
import { scopeKey, type KlicScope } from '../../src/klic/contracts';
import { KlicError } from './context';

type Stored = Conversation & { scope: KlicScope };
const valid = (v: unknown): v is Stored => {
  const c = v as Stored;
  return Boolean(c && typeof c.id === 'string' && c.scope && typeof c.scope.userId === 'string' && typeof c.scope.workspaceId === 'string' && Array.isArray(c.messages) && c.messages.every(m => typeof m.id === 'string' && typeof m.content === 'string' && ['user','assistant'].includes(m.role)));
};
export class ConversationStore {
  private summaries = new Map<string, { revision: string; value: Omit<Conversation, 'messages'> }>();
  private revision(filename: string) {
    const stat = statSync(filename);
    return `${stat.ino}:${stat.size}:${stat.mtimeMs}:${stat.ctimeMs}`;
  }
  private cache(filename: string, data: Stored) {
    const { messages, scope, ...value } = data;
    if (this.summaries.size >= 2048) this.summaries.delete(this.summaries.keys().next().value!);
    this.summaries.set(filename, { revision: this.revision(filename), value });
    return value;
  }
  constructor(readonly root = process.env.CLICKO_CONVERSATIONS_DIR || path.resolve('.clicko-data/conversations')) {
    for (const publicRoot of ['public','dist']) {
      const relative = path.relative(path.resolve(publicRoot), path.resolve(root));
      if (!relative || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative))) throw new Error('KLIC_PRIVATE_STORAGE_REQUIRED');
    }
  }
  private folder(scope: KlicScope) { return path.join(this.root, createHash('sha256').update(scopeKey(scope)).digest('hex')); }
  private filename(scope: KlicScope, id: string) {
    if (!/^[a-f0-9-]{36}$/.test(id)) throw new KlicError('KLIC_INVALID_CONVERSATION',404);
    return path.join(this.folder(scope), id + '.json');
  }
  list(scope: KlicScope) {
    const folder = this.folder(scope);
    if (!existsSync(folder)) return [];
    return readdirSync(folder).filter(n => /^[a-f0-9-]{36}\.json$/.test(n)).map(n => {
      const filename=path.join(folder,n);
      const cached=this.summaries.get(filename);
      if(cached?.revision===this.revision(filename))return cached.value;
      return this.cache(filename,this.read(scope,n.slice(0,-5)));
    }).sort((a,b) => b.updatedAt.localeCompare(a.updatedAt));
  }
  read(scope: KlicScope, id: string): Stored {
    const filename = this.filename(scope,id);
    if (!existsSync(filename)) throw new KlicError('KLIC_CONVERSATION_NOT_FOUND',404);
    const data = new AtomicJsonStore(filename,valid).load(null as unknown as Stored);
    if (scopeKey(data.scope) !== scopeKey(scope)) throw new KlicError('KLIC_SCOPE_MISMATCH',403);
    this.cache(filename,data);
    return data;
  }
  create(scope: KlicScope) {
    if (this.list(scope).length >= 100) throw new KlicError('KLIC_CONVERSATION_LIMIT',413);
    mkdirSync(this.folder(scope),{ recursive:true, mode:0o700 });
    const timestamp = new Date().toISOString();
    const data: Stored = { id: randomUUID(), scope: { workspaceId: scope.workspaceId, userId: scope.userId, clientId: scope.clientId }, title:'Nova conversa', createdAt:timestamp, updatedAt:timestamp, messages:[] };
    new AtomicJsonStore(this.filename(scope,data.id),valid).load(data);
    this.cache(this.filename(scope,data.id),data);
    return data;
  }
  update(scope: KlicScope, id: string, change: (conversation: Stored) => void) {
    const filename=this.filename(scope,id);
    if(!existsSync(filename))throw new KlicError('KLIC_CONVERSATION_NOT_FOUND',404);
    const repo = new AtomicJsonStore(filename,valid);
    const data = repo.load(null as unknown as Stored);
    if(scopeKey(data.scope)!==scopeKey(scope))throw new KlicError('KLIC_SCOPE_MISMATCH',403);
    change(data); data.updatedAt = new Date().toISOString(); repo.save(data); this.cache(filename,data); return data;
  }
  clear(scope: KlicScope) {
    for (const { id } of this.list(scope)) {
      const filename = this.filename(scope,id); unlinkSync(filename);
      this.summaries.delete(filename);
      if (existsSync(filename + '.previous')) unlinkSync(filename + '.previous');
    }
  }
}
export function publicConversation(conversation: Stored): Conversation {
  const { scope, ...value } = conversation;
  return { ...value, messages: value.messages.map(message => ({ ...message, attachments: message.attachments?.map(({ text, dataUrl, ...file }) => file) })) };
}
export function modelWindow(messages: ChatMessage[], budget = 48000) {
  const complete = messages.filter(m => m.role === 'user' || m.status === 'complete');
  const selected: Array<{ role: string; content: string }> = [];
  let remaining = budget;
  for (const message of complete.slice().reverse()) {
    if (remaining <= 0) break;
    const content = message.content.slice(-remaining);
    selected.unshift({ role: message.role, content }); remaining -= content.length;
  }
  // Relevant earlier facts remain retrievable without treating omitted history as a summary.
  const query = complete.at(-1)?.content.toLowerCase() || '';
  const terms = query.match(/[\p{L}\p{N}]{4,}/gu) || [];
  const earlier = complete.slice(0, Math.max(0,complete.length-selected.length)).filter(m => terms.some(t => m.content.toLowerCase().includes(t))).slice(-4).map(m => ({ role:m.role,content:m.content.slice(0,1500) }));
  return { recent: selected, earlier, omitted: complete.length-selected.length-earlier.length };
}
