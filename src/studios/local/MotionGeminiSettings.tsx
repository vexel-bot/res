import React from 'react';
import { apiFetch } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { LocalSelect } from './LocalSelect';
import { motionGeminiError } from './motionGeminiModel';
export { motionGeminiError } from './motionGeminiModel';

export type MotionGeminiStatus = {
  available: boolean; hasCredential: boolean; enabled: boolean; model?: string | null;
  models: {id:string;label:string}[]; connectionStatus:string; freeTierVerified:boolean;
  inferenceReady:boolean; pendingReason?:string; externalBudgetUsd:number;
};

/** Secrets stay only in this transient input; never use LocalRoom.write/recovery. */
export function MotionGeminiSettings({workspaceId,documentId,revision,onStatus}:{workspaceId:string;documentId?:string;revision?:number;onStatus:(status:MotionGeminiStatus|undefined)=>void}) {
  const {development} = useAuth();
  const [status,setStatus] = React.useState<MotionGeminiStatus>();
  const [key,setKey] = React.useState('');
  const [visible,setVisible] = React.useState(false);
  const [busy,setBusy] = React.useState(false);
  const [error,setError] = React.useState('');
  const [probeResult,setProbeResult] = React.useState('');
  const callback=React.useRef(onStatus); callback.current=onStatus;
  const endpoint='/api/v1/studios/v1/agents/motion-gemini?workspace_id='+encodeURIComponent(workspaceId);
  const route=(suffix:string)=>endpoint.replace('?',suffix+'?');
  const accept=(value:MotionGeminiStatus)=>{setStatus(value);callback.current(value);};
  React.useEffect(()=>{
    if (!development?.enabled) return;
    const controller=new AbortController();
    void apiFetch<MotionGeminiStatus>(endpoint,{signal:controller.signal}).then(value=>{if(!controller.signal.aborted)accept(value);}).catch(()=>{if(!controller.signal.aborted)callback.current(undefined);});
    return ()=>{controller.abort();};
  },[endpoint,development?.enabled]);
  if(!development?.enabled||!status?.available)return null;
  async function run(action:()=>Promise<MotionGeminiStatus>) {
    if(busy)return; setBusy(true);setError('');setProbeResult('');
    try{accept(await action());}catch(e){setError(motionGeminiError(e instanceof Error?e.message:'Falha na configuração.'));}
    finally{setBusy(false);}
  }
  return <details className="lp-settings motion-gemini-settings"><summary>IA Experimental — Gemini · {status.enabled?'ativado':'desativado'}</summary>
    <p>Somente DEV. O Gemini planeja texto/JSON; a Clicko renderiza localmente. A KLIC não é alterada.</p>
    <p>Chave: {status.hasCredential?'Configurada':'Não configurada'} · orçamento externo R$ 0</p>
    <label>Chave Gemini experimental<input type={visible?'text':'password'} value={key} autoComplete="off" spellCheck={false} maxLength={8192}
      aria-label="Chave Gemini experimental" onChange={e=>setKey(e.target.value)}/></label>
    <div className="lp-actions"><button type="button" disabled={busy||!key} onClick={()=>setVisible(v=>!v)}>{visible?'Ocultar chave':'Mostrar chave'}</button>
      <button type="button" disabled={busy||!key.trim()} onClick={()=>{const submitted=key.trim();setKey('');setVisible(false);void run(()=>apiFetch(route('/key'),{method:'PUT',body:JSON.stringify({apiKey:submitted})}));}}>Cadastrar chave</button>
      <button type="button" disabled={busy||!status.hasCredential} onClick={()=>void run(()=>apiFetch(route('/test'),{method:'POST'}))}>Testar conexão · listar modelos</button>
    </div>
    <label>Modelo de planejamento<LocalSelect ariaLabel="Modelo Gemini experimental" disabled={busy||!status.models.length} value={status.model||''}
      options={[{value:'',label:'Selecione um modelo verificado'},...status.models.map(m=>({value:m.id,label:m.label+' · '+m.id}))]}
      onChange={model=>void run(()=>apiFetch(endpoint,{method:'PUT',body:JSON.stringify({enabled:status.enabled,model})}))}/></label>
    <p role="status">{status.connectionStatus==='catalog_verified'?'Catálogo acessível. Isso não comprova gratuidade nem a quota restante.':status.connectionStatus==='failed'?'A conexão falhou.':'Conexão ainda não testada.'}</p>
    {!status.freeTierVerified&&<p>Inferência bloqueada: a API de modelos não informa o faturamento. É necessária verificação operacional do Free Tier e das quotas, vinculada à chave e ao modelo, no servidor. Não ative faturamento.</p>}
    <div className="lp-actions"><button type="button" disabled={busy||!status.model} onClick={()=>void run(()=>apiFetch(endpoint,{method:'PUT',body:JSON.stringify({enabled:!status.enabled,model:status.model})}))}>{status.enabled?'Restaurar planejador anterior':'Ativar Gemini experimental'}</button>
      <button type="button" disabled={busy||!status.hasCredential} onClick={()=>void run(()=>apiFetch(route('/key'),{method:'DELETE'}))}>Remover chave</button>
      <button type="button" disabled={busy} onClick={()=>void run(()=>apiFetch(endpoint))}>Atualizar status</button></div>
    <button type="button" disabled={busy||!status.inferenceReady||!documentId||!revision} onClick={()=>void run(async()=>{
      const task=await apiFetch<{status:string;errorCode?:string}>(`/api/v1/studios/v1/documents/${encodeURIComponent(documentId!)}/agent-tasks`,{
        method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({expectedRevision:revision,planner:'gemini_experimental',probe:true,instruction:'Teste mínimo autorizado de conexão; não editar o projeto.'})});
      if(task.status!=='succeeded')throw new Error(task.errorCode||'A solicitação mínima falhou.');
      setProbeResult('Solicitação mínima validada. Nenhuma edição ou renderização foi aplicada.');
      return apiFetch(endpoint);
    })}>Testar solicitação mínima · somente após admissão gratuita</button>
    {error&&<p role="alert">{error}</p>}
    {probeResult&&<p role="status">{probeResult}</p>}
  </details>;
}
