import React from 'react';
import { apiFetch, apiFetchBlob } from '../../api';
import { craftApi } from '../craft/craftApi';
import { AutomaticMaterialEffects } from './AutomaticMaterialEffects';

type Material = {assetId:string;role:string;label:string;alignmentGroup:string};
type Kit = {id:string;revision:number;name:string;category:string;goal:string;description:string;visualIdentity:string;materials:Material[]};
type Recipe = {id:string;label:string;status:string;missing:string[];reason:string;checks:string[];limitation:string};
type State = {workspaceId:string;documentRevision?:number;canonical?:boolean;localEffects?:{segmentationAvailable:boolean;generativeWeightsInstalled:boolean};kits:Kit[];binding:{revision:number;kitId?:string;kitRevision?:number};roles:Record<string,string>;recipes:Recipe[];recommendedRecipeId?:string};
type Plan = {recipeId:string;planDigest:string;canApply:boolean;note:string;timeline:unknown};
const fresh = ():Kit => ({id:crypto.randomUUID(),revision:0,name:'',category:'physical',goal:'showcase',description:'',visualIdentity:'',materials:[]});

export function ProductMaterialsPanel({kind,id,disabled}:{kind:'project'|'document';id:string;disabled:boolean}) {
  const url = `/api/v1/studios/v1/materials/${kind}/${id}`;
  const [state,setState] = React.useState<State>();
  const [kit,setKit] = React.useState<Kit>(fresh);
  const [dirty,setDirty] = React.useState(false);
  const [busy,setBusy] = React.useState(false);
  const [effectBusy,setEffectBusy] = React.useState(false);
  const [role,setRole] = React.useState('product');
  const [error,setError] = React.useState('');
  const [notice,setNotice] = React.useState('');
  const [plan,setPlan] = React.useState<Plan>();
  const [cutout,setCutout] = React.useState<{material:Material;href:string;points:[number,number][]}>();
  const locked = disabled || busy || effectBusy;
  React.useEffect(()=>()=>{if(cutout?.href)URL.revokeObjectURL(cutout.href);},[cutout?.href]);
  React.useEffect(() => {
    const controller = new AbortController();
    void apiFetch<State>(url,{signal:controller.signal}).then(v => {
      setState(v);setKit(v.kits.find(k => k.id===v.binding.kitId)||fresh());
    }).catch(e => {if(!controller.signal.aborted)setError(e.message);});
    return () => controller.abort();
  },[url]);
  React.useEffect(() => {
    if(!dirty && !busy && !cutout && !effectBusy)return;
    const before = (e:Event) => {e.preventDefault();if('returnValue' in e)(e as BeforeUnloadEvent).returnValue='';};
    window.addEventListener('beforeunload',before);window.addEventListener('clicko:studio-before-leave',before);
    return () => {window.removeEventListener('beforeunload',before);window.removeEventListener('clicko:studio-before-leave',before);};
  },[dirty,busy,cutout,effectBusy]);
  function change(patch:Partial<Kit>) {setKit(k => ({...k,...patch}));setDirty(true);setPlan(undefined);setNotice('');}
  async function perform(action:()=>Promise<void>) {
    setBusy(true);setError('');setNotice('');
    try{await action();}catch(e){setError(e instanceof Error?e.message:'Não foi possível concluir. Seus dados locais foram mantidos.');}finally{setBusy(false);}
  }
  async function refresh() {const v=await apiFetch<State>(url);setState(v);return v;}
  async function save() {
    await perform(async () => {
      const {id:kitId,revision,...data}=kit;
      const saved=await apiFetch<Kit>(`${url}/kits/${kitId}`,{method:'PUT',body:JSON.stringify({...data,expectedRevision:revision})});
      setKit(saved);setDirty(false);await refresh();setNotice('Materiais salvos. Vincule esta versão ao anúncio para usá-la no planejamento.');
    });
  }
  async function bind() {
    if(!state||dirty)return;
    await perform(async () => {
      await apiFetch<State>(`${url}/binding`,{method:'PUT',body:JSON.stringify({expectedRevision:state.binding.revision,kitId:kit.id,kitRevision:kit.revision})});await refresh();
      setPlan(undefined);setNotice('Versão dos materiais vinculada. As opções de edição foram atualizadas.');
    });
  }
  async function upload(files:FileList|null) {
    if(!state||!files?.length)return;
    await perform(async () => {
      for(const file of Array.from(files)) {
        const asset=await craftApi.uploadAsset(state.workspaceId,file);
        setKit(k => ({...k,materials:[...k.materials,{assetId:asset.id,role,label:file.name,alignmentGroup:''}]}));
        setDirty(true);
      }
      setPlan(undefined);setNotice('Arquivos enviados. Confira os papéis e salve os materiais.');
    });
  }
  async function preview(recipeId:string) {
    await perform(async () => {setPlan(await apiFetch<Plan>(`${url}/preview`,{method:'POST',body:JSON.stringify({recipeId,requestKey:crypto.randomUUID()})}));});
  }
  async function apply() {
    if(!plan)return;
    if(!window.dispatchEvent(new Event('clicko:studio-before-leave',{cancelable:true}))){setError('Salve ou descarte os ajustes locais antes de inserir o estudo.');return;}
    await perform(async () => {
      await apiFetch(`${url}/apply`,{method:'POST',body:JSON.stringify({recipeId:plan.recipeId,planDigest:plan.planDigest,requestKey:crypto.randomUUID()})});
      setPlan(undefined);setNotice('Estudo inserido. Reabra o projeto para visualizar e exportar.');
      window.dispatchEvent(new CustomEvent('clicko:materials-composition-applied',{detail:{documentId:id}}));
    });
  }
  async function importMaterials() {
    if(!window.dispatchEvent(new Event('clicko:studio-before-leave',{cancelable:true}))){setError('Salve ou descarte os ajustes locais antes de disponibilizar os materiais.');return;}
    await perform(async()=>{
      const current=await refresh();
      await apiFetch(`${url}/import`,{method:'POST',body:JSON.stringify({expectedRevision:current.documentRevision,requestKey:crypto.randomUUID()})});
      await refresh();setPlan(undefined);setNotice('Materiais disponíveis para a edição e para o planejamento por IA. Nenhuma chamada de IA foi feita.');
      window.dispatchEvent(new CustomEvent('clicko:materials-composition-applied',{detail:{documentId:id}}));
    });
  }
  async function openCutout(material:Material) {
    await perform(async()=>{const blob=await apiFetchBlob(`/api/v1/assets/${encodeURIComponent(material.assetId)}/content`);if(!blob.type.startsWith('image/'))throw new Error('O recorte por contorno requer uma imagem. Para vídeo, use uma máscara sincronizada.');setCutout({material,href:URL.createObjectURL(blob),points:[]});});
  }
  async function prepareCutout() {
    if(!cutout)return;
    await perform(async()=>{
      const result=await apiFetch<{assetId:string;label:string}>(`${url}/cutout`,{method:'POST',body:JSON.stringify({sourceAssetId:cutout.material.assetId,points:cutout.points,featherPixels:1})});
      setKit(k=>({...k,materials:[...k.materials,{assetId:result.assetId,label:result.label,role:'product_cutout',alignmentGroup:cutout.material.alignmentGroup}]}));
      setDirty(true);setPlan(undefined);setCutout(undefined);setNotice('Recorte preparado. Confira o papel do arquivo e salve os materiais.');
    });
  }
  const bound = state?.binding.kitId===kit.id && state.binding.kitRevision===kit.revision && !dirty;
  return <details className="ad-copy-group product-materials"><summary>Materiais do produto ou serviço e direção de edição</summary>
    <p>Reúna logo, identidade, produtos, demonstrações e cenas. Cada conjunto pode ser reutilizado nos anúncios deste cliente.</p>
    {state && <>
      <label htmlFor={`kit-select-${id}`}>Conjunto salvo</label>
      <select id={`kit-select-${id}`} value={kit.revision?kit.id:''} disabled={locked||dirty||Boolean(cutout)} onChange={e => {setKit(state.kits.find(k=>k.id===e.target.value)||fresh());setPlan(undefined);}}>
        <option value="">Novo produto ou serviço</option>{state.kits.map(k => <option key={k.id} value={k.id}>{k.name} · versão {k.revision}</option>)}
      </select>
      {dirty && <p role="status">Alterações ainda não salvas. <button type="button" disabled={locked} onClick={()=>{setKit(state.kits.find(k=>k.id===kit.id)||fresh());setDirty(false);setPlan(undefined);}}>Descartar alterações locais</button></p>}
      <fieldset disabled={locked}>
        <label htmlFor={`kit-name-${id}`}>Nome do produto ou serviço</label><input id={`kit-name-${id}`} maxLength={240} value={kit.name} onChange={e=>change({name:e.target.value})}/>
        <label htmlFor={`kit-category-${id}`}>Tipo</label><select id={`kit-category-${id}`} value={kit.category} onChange={e=>change({category:e.target.value})}>
          <option value="physical">Produto físico</option><option value="software">Software / aplicativo</option><option value="service">Serviço</option><option value="other">Outro</option>
        </select>
        <label htmlFor={`kit-goal-${id}`}>O que a edição deve ajudar a mostrar</label><select id={`kit-goal-${id}`} value={kit.goal} onChange={e=>change({goal:e.target.value})}>
          <option value="showcase">Apresentar o produto</option><option value="demonstrate">Demonstrar o funcionamento</option><option value="explain">Explicar uma vantagem</option><option value="variants">Comparar variantes</option><option value="transformation">Mostrar uma transformação</option>
        </select>
        <label htmlFor={`kit-description-${id}`}>Descrição e contexto dos materiais</label><textarea id={`kit-description-${id}`} rows={3} maxLength={6000} value={kit.description} onChange={e=>change({description:e.target.value})}/>
        <label htmlFor={`kit-identity-${id}`}>Cores, fontes e regras da marca</label><textarea id={`kit-identity-${id}`} rows={3} maxLength={6000} value={kit.visualIdentity} onChange={e=>change({visualIdentity:e.target.value})}/>
        <label htmlFor={`kit-role-${id}`}>Papel dos próximos arquivos</label><select id={`kit-role-${id}`} value={role} onChange={e=>setRole(e.target.value)}>{Object.entries(state.roles).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select>
        <label htmlFor={`kit-upload-${id}`}>Adicionar arquivos</label><input id={`kit-upload-${id}`} type="file" multiple accept="image/*,video/*,audio/*,application/pdf,text/plain" onChange={e=>{void upload(e.target.files);e.target.value='';}}/>
        <p>Recortes e molduras devem ser PNG com transparência. Máscaras em cinza podem ser imagens ou vídeos sincronizados. Para fontes que devem coincidir, informe o mesmo grupo de alinhamento.</p>
        <details><summary>{kit.materials.length} arquivos · revisar papéis, alinhamento e recortes</summary><ul>{kit.materials.map((m,index)=><li key={`${m.assetId}:${index}`}>
          <span>{m.label}</span>{' '}
          <select aria-label={`Papel de ${m.label}`} value={m.role} onChange={e=>change({materials:kit.materials.map((v,i)=>i===index?{...v,role:e.target.value}:v)})}>{Object.entries(state.roles).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select>
          <input aria-label={`Grupo de alinhamento de ${m.label}`} placeholder="Ex.: produto-01 / tomada-01" maxLength={120} value={m.alignmentGroup} onChange={e=>change({materials:kit.materials.map((v,i)=>i===index?{...v,alignmentGroup:e.target.value}:v)})}/>
          <button type="button" onClick={()=>change({materials:kit.materials.filter((_,i)=>i!==index)})}>Remover da seleção</button>
          <button type="button" disabled={Boolean(cutout)} onClick={()=>void openCutout(m)}>Preparar recorte de imagem</button>
        </li>)}</ul></details>
      </fieldset>
      {cutout&&<div><p>Clique ao redor do objeto para definir o contorno. O recorte mantém o tamanho e a posição da imagem original. Para cabelo, movimento ou bordas delicadas, use uma máscara especializada.</p>
        <div style={{position:'relative',maxWidth:420,lineHeight:0}}>
          <img alt={`Definir contorno de ${cutout.material.label}`} src={cutout.href} style={{width:'100%',display:'block'}} onClick={e=>{
            if(locked||cutout.points.length>=128)return;const r=e.currentTarget.getBoundingClientRect();const p:[number,number]=[Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))];
            setCutout(c=>c?{...c,points:[...c.points,p]}:c);
          }}/>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true" style={{position:'absolute',inset:0,width:'100%',height:'100%',pointerEvents:'none'}}><polygon points={cutout.points.map(([x,y])=>`${x*100},${y*100}`).join(' ')} fill="#29d3a133" stroke="#29d3a1" strokeWidth="0.7"/>{cutout.points.map(([x,y],i)=><circle key={i} cx={x*100} cy={y*100} r="1" fill="white"/>)}</svg>
        </div>
        <p>{cutout.points.length} pontos definidos.</p><button type="button" disabled={locked||!cutout.points.length} onClick={()=>setCutout(c=>c?{...c,points:c.points.slice(0,-1)}:c)}>Desfazer ponto</button>{' '}<button type="button" disabled={locked||cutout.points.length<3} onClick={()=>void prepareCutout()}>Criar PNG recortado</button>{' '}<button type="button" disabled={locked} onClick={()=>setCutout(undefined)}>Cancelar recorte</button>
      </div>}
      <div className="ad-copy-actions"><button type="button" disabled={locked||Boolean(cutout)||!kit.name.trim()||!dirty} onClick={()=>void save()}>Salvar materiais</button><button type="button" disabled={locked||Boolean(cutout)||dirty||!kit.revision||bound} onClick={()=>void bind()}>Usar esta versão neste anúncio</button></div>
      <p>{bound?'Este anúncio usa esta versão dos materiais.':'Vincule uma versão salva para atualizar a direção de edição.'}</p>
      {bound&&state.canonical&&state.localEffects?.segmentationAvailable&&<AutomaticMaterialEffects key={`${id}:${kit.id}`} id={id} workspaceId={state.workspaceId} kitRevision={kit.revision} materials={kit.materials} disabled={disabled||busy||dirty||Boolean(cutout)} canGenerate={state.localEffects.generativeWeightsInstalled} onBusy={setEffectBusy} onComplete={refresh}/>}
      {bound&&state.canonical&&<button type="button" disabled={locked||Boolean(cutout)} onClick={()=>void importMaterials()}>Disponibilizar materiais para edição</button>}
      {bound && <div><h4>Opções conforme objetivo e materiais</h4><p>A recomendação considera o que precisa ser mostrado e os arquivos disponíveis. A qualidade será conferida no vídeo exportado.</p>
        {state.recipes.map(r=><details key={r.id}><summary>{r.label}{state.recommendedRecipeId===r.id?' · recomendada':''} · {r.status==='ready_to_compose'?'materiais disponíveis':'faltam materiais'}</summary><p>{r.reason}</p>{r.missing.length>0&&<p>Necessário: {r.missing.join('; ')}.</p>}<p>Conferir: {r.checks.join('; ')}.</p><small>{r.limitation}</small><p><button type="button" disabled={locked||r.status!=='ready_to_compose'} onClick={()=>void preview(r.id)}>Preparar estudo de 6 segundos</button></p></details>)}
      </div>}
      {plan && <div role="status"><p>{plan.note}</p>{kind==='document'&&plan.canApply?<button type="button" disabled={locked||dirty} onClick={()=>void apply()}>Inserir estudo na timeline vazia</button>:<p>O estudo pode orientar a edição. Para inserção direta, abra um projeto canônico com timeline vazia.</p>}<details><summary>Ver plano do estudo</summary><pre style={{maxHeight:240,overflow:'auto'}}>{JSON.stringify(plan.timeline,null,2)}</pre></details></div>}
    </>}
    {notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}
  </details>;
}
