import React from 'react';
import { useKlicClient } from './useKlicClient';
import type { ChatFile } from './conversation';
import { ClickoLoader } from '../components/ClickoLoader';

export const ChatAttachment=React.memo(function ChatAttachment({file,conversationId}:{file:ChatFile;conversationId:string}) {
  const {workspaceId,clientId}=useKlicClient();
  const [url,setUrl]=React.useState('');const [error,setError]=React.useState('');const [loading,setLoading]=React.useState(false);
  const urlRef=React.useRef('');const pending=React.useRef<AbortController | null>(null);
  React.useEffect(()=>()=>{pending.current?.abort();if(urlRef.current)URL.revokeObjectURL(urlRef.current);},[]);
  const load=async()=>{
    if(pending.current)return;
    const controller=new AbortController();pending.current=controller;setLoading(true);setError('');
    try {
      const response=await fetch('/api/klic/conversations/file',{method:'POST',signal:controller.signal,credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({workspaceId,clientId,conversationId,fileId:file.id})});
      if(!response.ok)throw new Error('Não foi possível abrir este anexo.');
      const blob=await response.blob();if(controller.signal.aborted)return;
      if(urlRef.current)URL.revokeObjectURL(urlRef.current);
      urlRef.current=URL.createObjectURL(blob);setUrl(urlRef.current);
    }catch(e){if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Anexo indisponível.');}
    finally{pending.current=null;if(!controller.signal.aborted)setLoading(false);}
  };
  return <div className="max-w-full rounded-lg border border-white/10 px-2 py-1 text-[10px]">
    <button onClick={()=>void load()} disabled={loading||Boolean(url)} className="break-all text-left">{loading && <ClickoLoader size="tiny" label="Abrindo anexo" className="mr-2" />}{file.name} · {Math.ceil(file.size/1024)} KB{loading?' · Abrindo…':''}</button>
    {error&&<p role="status">{error}</p>}
    {url&&file.type.startsWith('image/')&&<img src={url} alt={file.name} className="mt-2 max-h-56 max-w-full rounded object-contain" />}
    {url&&file.type.startsWith('audio/')&&<audio src={url} controls className="mt-2 max-w-full" />}
    {url&&<a href={url} download={file.name} className="ml-2 text-[#FF7F50]">Baixar</a>}
  </div>;
});
