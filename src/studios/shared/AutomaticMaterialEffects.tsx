import React from 'react';
import {apiFetch,apiFetchBlob,APIError} from '../../api';

type Result={downloadUrl:string;documentId:string;preparedKitId:string;operation:string;externalCostUsd:number;report?:{camera?:{applied:boolean}}};
type Job={id:string;status:string;progress:number;result?:Result;errorMessage?:string};
const active=(job?:Job)=>Boolean(job&&!['succeeded','failed','cancelled'].includes(job.status));
const statusLabel:Record<string,string>={queued:'Na fila',running:'Processando',retrying:'Tentando novamente',cancel_requested:'Cancelando',cancelled:'Cancelado',failed:'Falhou',succeeded:'Concluído'};
const worlds=[['Estúdio criativo','A spacious modern creative studio interior, wooden desk, large windows, plants, cinematic teal and warm gold lighting, photorealistic architecture, no people'],
 ['Loja minimalista','A beautiful modern minimalist retail store interior, clean shelves, soft commercial photography lighting, elegant white walls, no people'],
 ['Jardim tropical','A beautiful lush tropical garden, wooden terrace, sunlight through plants, cinematic photographic background, no people']];
export function AutomaticMaterialEffects({id,workspaceId,kitRevision,materials,disabled,canGenerate,onBusy,onComplete}:{
 id:string;workspaceId:string;kitRevision:number;materials:{assetId:string;role:string;label:string}[];disabled:boolean;canGenerate:boolean;
 onBusy:(busy:boolean)=>void;onComplete:()=>Promise<unknown>;
}){
 const base=`/api/v1/studios/v1/materials/document/${id}`;
 const recovery=`clicko:local-effect:${workspaceId}:${id}`;
 const [job,setJob]=React.useState<Job>();const [submitting,setSubmitting]=React.useState(false);const [error,setError]=React.useState('');
 const [source,setSource]=React.useState('');const [operation,setOperation]=React.useState('segment_person');
 const [prompt,setPrompt]=React.useState(worlds[0][1]);const [duration,setDuration]=React.useState(6);
 const [pending,setPending]=React.useState<Record<string,unknown>>();const [video,setVideo]=React.useState<string>();
 const [auxBusy,setAuxBusy]=React.useState(false);
 React.useEffect(()=>()=>{if(video)URL.revokeObjectURL(video);},[video]);
 React.useEffect(()=>{let live=true;const raw=sessionStorage.getItem(recovery);if(raw){try{const value=JSON.parse(raw);if(value.jobId)void apiFetch<Job>(`/api/v1/studios/v1/jobs/${value.jobId}`).then(v=>{if(live)setJob(v);}).catch(e=>{if(live)setError(e.message);});if(value.pending)setPending(value.pending);}catch{setError('Não foi possível recuperar o pedido local.');}}return()=>{live=false;};},[recovery]);
 React.useEffect(()=>{onBusy(submitting||active(job)||auxBusy||Boolean(pending));return()=>onBusy(false);},[submitting,job?.status,auxBusy,pending,onBusy]);
 React.useEffect(()=>{if(!active(job))return;const c=new AbortController();const timer=setTimeout(()=>{
   void apiFetch<Job>(`/api/v1/studios/v1/jobs/${job!.id}`,{signal:c.signal}).then(async next=>{setJob(next);if(next.status==='succeeded')await onComplete();}).catch(e=>{if(!c.signal.aborted)setError(e.message);});
 },1500);return()=>{c.abort();clearTimeout(timer);};},[job]);
 async function submit(){
  if(submitting||active(job))return;setSubmitting(true);setError('');
  try{const current=await apiFetch<{documentRevision:number}>(base);const request=pending||{expectedRevision:current.documentRevision,kitRevision,requestKey:crypto.randomUUID(),sourceAssetId:source,operation,prompt:operation==='segment_person'?'':prompt,durationSeconds:duration,...(operation==='localized_edit'?{region:[.55,.1,.4,.65]}:{})};
   setPending(request);sessionStorage.setItem(recovery,JSON.stringify({pending:request}));
   const next=await apiFetch<Job>(base+'/effects',{method:'POST',body:JSON.stringify(request)});setJob(next);setPending(undefined);sessionStorage.setItem(recovery,JSON.stringify({jobId:next.id}));
  }catch(e){if(e instanceof APIError&&[400,403,404,409,422].includes(e.status)){setPending(undefined);sessionStorage.removeItem(recovery);}setError(e instanceof Error?e.message:'Não foi possível iniciar. Repita o mesmo pedido para conferir.');}finally{setSubmitting(false);}
 }
 async function preview(){if(!job?.result)return;setAuxBusy(true);setError('');try{const blob=await apiFetchBlob(job.result.downloadUrl);setVideo(URL.createObjectURL(blob));}catch(e){setError((e as Error).message);}finally{setAuxBusy(false);}}
 const locked=disabled||submitting||active(job)||Boolean(pending);
 return <details><summary>Preparação automática e efeitos locais</summary>
  <p>A Clicko prepara a máscara temporal e exporta uma cópia editável. A geração local altera o cenário ou uma região, preservando a pessoa e a área inferior de interação com objetos. Confira bordas, sombras e coerência antes de aprovar.</p>
  <fieldset disabled={locked}><label htmlFor={`effect-source-${id}`}>Vídeo de origem</label><select id={`effect-source-${id}`} value={source} onChange={e=>setSource(e.target.value)}><option value="">Escolha um vídeo dos materiais…</option>{materials.filter(m=>['presenter','demo'].includes(m.role)).map(m=><option value={m.assetId} key={`${m.assetId}:${m.role}`}>{m.label}</option>)}</select>
   <label htmlFor={`effect-operation-${id}`}>Efeito</label><select id={`effect-operation-${id}`} value={operation} onChange={e=>setOperation(e.target.value)}><option value="segment_person">Recortar automaticamente a pessoa em movimento</option><option value="replace_background" disabled={!canGenerate}>Transformar o cenário com IA local</option><option value="localized_edit" disabled={!canGenerate}>Alterar a região direita com IA local</option></select>
   {operation!=='segment_person'&&<><label htmlFor={`effect-world-${id}`}>Novo ambiente</label><select id={`effect-world-${id}`} value={prompt} onChange={e=>setPrompt(e.target.value)}>{worlds.map(([label,value])=><option value={value} key={label}>{label}</option>)}</select></>}
   <label htmlFor={`effect-duration-${id}`}>Duração do trecho (segundos)</label><input id={`effect-duration-${id}`} type="number" min={2} max={12} value={duration} onChange={e=>setDuration(Math.max(2,Math.min(12,Math.round(Number(e.target.value)||2))))}/>
  </fieldset>
  <button type="button" disabled={disabled||submitting||active(job)||(!source&&!pending)} onClick={()=>void submit()}>{pending?'Conferir o mesmo pedido':'Preparar e executar localmente'}</button>
  <p>Processamento local, sem API paga. {operation==='localized_edit'?'A região direita é composta sobre o vídeo e permanece atrás da pessoa. A câmera ainda exige revisão.':''}</p>
  {job&&<p role="status">{statusLabel[job.status]||job.status} · {job.progress}% {job.errorMessage?'O processamento local falhou. O diagnóstico foi registrado para conferência.':''}</p>}
  {active(job)&&<button type="button" onClick={()=>void apiFetch<Job>(`/api/v1/studios/v1/jobs/${job!.id}/cancel`,{method:'POST',body:JSON.stringify({reason:'Cancelamento solicitado na preparação automática'})}).then(setJob).catch(e=>setError(e.message))}>Cancelar processamento local</button>}
  {job?.status==='succeeded'&&job.result&&<div><p>{job.result.report?.camera?.applied===false?'A câmera saiu da faixa de rastreamento. O vídeo original foi preservado.':'Vídeo pronto para revisão. Os materiais preparados estão salvos em um novo conjunto.'} Custo de API: US$ {job.result.externalCostUsd}.</p><button type="button" disabled={auxBusy} onClick={()=>void preview()}>Visualizar resultado local</button>{' '}<button type="button" disabled={auxBusy} onClick={()=>{if(!window.dispatchEvent(new Event('clicko:studio-before-leave',{cancelable:true}))){setError('Salve ou descarte os ajustes locais antes de abrir a cópia.');return;}window.dispatchEvent(new CustomEvent('clicko:open-prepared-document',{detail:{documentId:job.result!.documentId}}));}}>Abrir cópia editável</button>{video&&<video controls src={video} style={{width:'100%',maxWidth:720}} aria-label="Resultado do efeito local"/>}</div>}
  {error&&<p role="alert">{error}</p>}
 </details>;
}
