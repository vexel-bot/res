import React from 'react';
import type { ChatAttachmentInput, Conversation, ChatMessage } from './conversation';
import { useKlicClient } from './useKlicClient';
import { consumeKlicStream, readKlicJson } from './transport';
import { KLIC_MODULES } from './contracts';

export function useConversations() {
  const klic=useKlicClient();
  const client=React.useRef(klic); client.current=klic;
  const loadedScope=React.useRef(klic.scope);
  const [conversation,setConversation]=React.useState<Conversation | null>(null);
  const current=React.useRef(conversation); current.current=conversation;
  const [conversations,setConversations]=React.useState<Omit<Conversation,'messages'>[]>([]);
  const [loading,setLoading]=React.useState(false);
  const [phase,setPhase]=React.useState('');
  const [error,setError]=React.useState('');
  const pending=React.useRef<AbortController | null>(null);
  const generation=React.useRef(0);
  const hydrated=React.useRef(false);
  const switching=React.useRef(false);
  const key=`clicko:klic:conversation:${klic.scope}`;
  const storageKey=React.useRef(key); storageKey.current=key;
  const select=React.useCallback((value: Conversation | null)=>{
    current.current=value; setConversation(value);
    try { if (value) localStorage.setItem(storageKey.current,value.id); else localStorage.removeItem(storageKey.current); } catch { /* Server history remains authoritative. */ }
  },[]);
  const refresh=React.useCallback(async ()=>{
    const scope=client.current.scope;
    const result=await client.current.request<{conversations:Omit<Conversation,'messages'>[]}>('conversations/list','ai-chat');
    if (scope===client.current.scope) setConversations(result.conversations);
    return result.conversations;
  },[]);
  React.useEffect(()=>{
    const epoch=++generation.current; pending.current?.abort(); pending.current=null;
    loadedScope.current=klic.scope;
    switching.current=false;
    hydrated.current=false; current.current=null; setConversation(null); setConversations([]); setLoading(true); setPhase('Carregando conversas…'); setError('');
    const controller=new AbortController();
    void (async()=>{
      try {
        const result=await client.current.request<{conversations:Omit<Conversation,'messages'>[]}>('conversations/list','ai-chat',{},controller.signal);
        if (epoch!==generation.current) return; setConversations(result.conversations);
        if(!result.conversations.length){
          let legacy:unknown;
          try { const parsed=JSON.parse(localStorage.getItem(`clicko:ai-chat:v2:${client.current.scope}`)||'null');legacy=Array.isArray(parsed)?parsed:parsed?.messages; } catch { /* Never change the old backup on an unreadable value. */ }
          if(Array.isArray(legacy)){
            const messages=legacy.filter(m=>m?.module!=='create-image'&&m?.module!=='create-video'&&!String(m?.id).startsWith('welcome-'));
            if(messages.length){
              const imported=await client.current.request<Conversation>('conversations/import','ai-chat',{messages},controller.signal);
              if(epoch===generation.current){select(imported);setConversations([imported]);}return;
            }
          }
        }
        let id:string | null=null; try { id=localStorage.getItem(key); } catch { /* Preference optional. */ }
        if (id && result.conversations.some(c=>c.id===id)) {
          const value=await client.current.request<Conversation>('conversations/read','ai-chat',{conversationId:id},controller.signal);
          if (epoch===generation.current) select(value);
        }
      } catch (e) { if (!controller.signal.aborted && epoch===generation.current) setError(e instanceof Error ? e.message : 'Não foi possível carregar as conversas.'); }
      finally { if(epoch===generation.current){hydrated.current=true;setLoading(false);setPhase('');} }
    })();
    return ()=>{ generation.current++; controller.abort(); pending.current?.abort(); };
  },[klic.scope,key,select]);
  const cancel=React.useCallback(()=>{ pending.current?.abort(); },[]);
  const openConversation=React.useCallback(async(id:string)=>{
    if(pending.current || switching.current || !hydrated.current) return;
    const epoch=++generation.current; switching.current=true;setLoading(true);setPhase('Carregando conversa…');setError('');
    try { const value=await client.current.request<Conversation>('conversations/read','ai-chat',{conversationId:id}); if(epoch===generation.current)select(value); }
    catch(e){if(epoch===generation.current)setError(e instanceof Error?e.message:'Não foi possível abrir a conversa.');}
    finally {if(epoch===generation.current){switching.current=false;setLoading(false);setPhase('');}}
  },[select]);
  const newConversation=React.useCallback(()=>{ if(pending.current || switching.current || !hydrated.current)return; generation.current++; select(null); setError(''); },[select]);
  const clearHistory=React.useCallback(()=>{
    if(pending.current || switching.current || !hydrated.current)return;
    const epoch=generation.current;
    switching.current=true;setLoading(true);
    void client.current.request('conversations/clear','ai-chat').then(()=>{if(epoch===generation.current){select(null);setConversations([]);}}).catch(e=>{if(epoch===generation.current)setError(e.message);}).finally(()=>{if(epoch===generation.current){switching.current=false;setLoading(false);}});
  },[select]);
  const send=React.useCallback(async(content:string,attachments:ChatAttachmentInput[]=[],retryId?:string,actionId?:string)=>{
    if(!hydrated.current || switching.current)throw new Error('Aguarde o carregamento das conversas.');
    if(pending.current || (!content.trim()&&!attachments.length&&!retryId))return;
    const controller=new AbortController();pending.current=controller;
    const timeout=setTimeout(()=>controller.abort(new DOMException('O servidor demorou demais para responder. Tente novamente.','TimeoutError')),100000);
    const epoch=generation.current; const requestId=retryId||crypto.randomUUID();
    setLoading(true);setPhase('Preparando mensagem…');setError('');
    let active=current.current; let buffer=''; let flushTimer:ReturnType<typeof setTimeout>|undefined;
    const activeNow=()=>generation.current===epoch && !controller.signal.aborted;
    const flush=()=>{
      if(!buffer || generation.current!==epoch)return;
      const delta=buffer;buffer='';
      setConversation(c=> c ? {...c,messages:c.messages.map(m=>m.id===requestId+'-reply'?{...m,content:m.content+delta,status:'streaming'}:m)}:c);
    };
    try {
      if(!active) {active=await client.current.request<Conversation>('conversations/create','ai-chat',{},controller.signal);if(!activeNow())return;select(active);}
      if(!retryId){
        const optimistic:ChatMessage={id:requestId,requestId,role:'user',content,attachments:attachments.map((f,i)=>({id:`pending-${i}`,name:f.name,type:f.type,size:f.size})),createdAt:new Date().toISOString(),module:'ai-chat',status:'pending'};
        select({...active,messages:[...active.messages,optimistic]});
      }
      setPhase('Enviando e processando…');
      const c=client.current;
      const source=KLIC_MODULES.includes(c.pageContext.module)?c.pageContext.module:'ai-chat';
      const response=await fetch('/api/klic/conversations/send',{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({conversationId:active.id,requestId,message:content,actionId,attachments,retry:Boolean(retryId),workspaceId:c.workspaceId,clientId:c.clientId,source,pageContext:{...c.pageContext,module:source},productionContext:c.studioContext,context:c.snapshot})});
      if(!response.ok)await readKlicJson(response);
      if(response.headers.get('content-type')?.includes('application/json')){const data=await readKlicJson<Conversation>(response);if(activeNow())select(data);return;}
      if(!response.body)throw new Error('A conexão não permite receber a resposta.');
      await consumeKlicStream(response.body,event=>{
            if(!activeNow())throw controller.signal.reason || new DOMException('O contexto ativo mudou.','AbortError');
            if(event.type==='accepted'){select(event.data);setPhase('Gerando resposta…');}
            if(event.type==='phase')setPhase(event.data==='transcribing'?'Transcrevendo áudio…':'Gerando resposta…');
            if(event.type==='delta'){buffer+=event.data;if(!flushTimer)flushTimer=setTimeout(()=>{flushTimer=undefined;flush();},50);}
            if(event.type==='done'){clearTimeout(flushTimer);buffer='';select(event.data);}
            if(event.type==='error'){clearTimeout(flushTimer);buffer='';select(event.data.conversation);setError(event.data.message);}
      });
    } catch(e){
      if(generation.current!==epoch)return;
      flush();setError(controller.signal.aborted?controller.signal.reason?.name==='TimeoutError'?controller.signal.reason.message:'Resposta interrompida.':e instanceof TypeError?'Não foi possível conectar à Clicko. Verifique sua conexão e tente novamente.':e instanceof Error?e.message:'Não foi possível consultar a KLIC.');
      // Reconcile with the server; never silently turn optimistic messages into persisted history.
      const recovery=new AbortController();const recoveryTimer=setTimeout(()=>recovery.abort(),5000);
      try {
      if(controller.signal.aborted)try{await client.current.request('conversations/cancel','ai-chat',{requestId},recovery.signal);}catch{/* A disconnected server will reconcile interrupted requests on the next read. */}
      if(active)try{const saved=await client.current.request<Conversation>('conversations/read','ai-chat',{conversationId:active.id},recovery.signal);if(generation.current===epoch){
        if(!saved.messages.some(m=>m.id===requestId))setError('Não foi possível enviar. O texto e os anexos continuam disponíveis no campo de mensagem.');
        select(saved);
        if(saved.messages.some(m=>m.id===requestId))return;
      }}catch{/* Keep the last known state, visibly marked as pending until reconnection. */}
      } finally {clearTimeout(recoveryTimer);}
      throw e;
    } finally {clearTimeout(timeout);clearTimeout(flushTimer);if(generation.current===epoch){pending.current=null;setLoading(false);setPhase('');void refresh().catch(()=>{});}}
  },[refresh,select]);
  const retry=React.useCallback(()=>{const m=current.current?.messages.at(-1);if(m?.role==='assistant'&&['error','cancelled'].includes(m.status))void send('',[],m.requestId).catch(()=>{});},[send]);
  const toggleFavorite=React.useCallback((id:string)=>{
    if(!current.current || pending.current)return;
    const conversationId=current.current.id;
    const epoch=generation.current;
    void client.current.request<Conversation>('conversations/favorite','ai-chat',{conversationId,messageId:id}).then(value=>{
      if(generation.current!==epoch || current.current?.id!==conversationId)return;
      const favorite=value.messages.find(message=>message.id===id)?.favorite;
      setConversation(conversation=>{
        if(conversation?.id!==conversationId)return conversation;
        const updated={...conversation,messages:conversation.messages.map(message=>message.id===id?{...message,favorite}:message)};
        current.current=updated;
        return updated;
      });
    }).catch(e=>{if(generation.current===epoch)setError(e.message);});
  },[select]);
  const visible=loadedScope.current===klic.scope;
  return {messages:visible?conversation?.messages||[]:[],conversationId:visible?conversation?.id:undefined,conversations:visible?conversations:[],loading:visible?loading:true,phase,error:visible?error:'',send,openConversation,newConversation,clearHistory,cancel,retry,toggleFavorite};
}
