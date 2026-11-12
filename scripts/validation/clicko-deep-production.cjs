/** One real, resumable Clicko generation. Never changes or bypasses the USD cap. */
const fs=require('node:fs'),path=require('node:path');
const {execFileSync}=require('node:child_process');
const {request,get,base,hash,state:lab}=require('./clicko-motion-editorial-proof.cjs');
if(!process.argv[2]||!process.argv[3])throw Error('Provide existing laboratory and separate output directory.');
const root=path.resolve(process.argv[3]);fs.mkdirSync(root,{recursive:true});
const receipt=path.join(root,'recibo.json');
const state=fs.existsSync(receipt)?JSON.parse(fs.readFileSync(receipt)):{};
const key='clicko-open-xhigh-20261110-v1';
const save=()=>fs.writeFileSync(receipt,JSON.stringify(state,null,2));
const referenceRoot='C:/Users/edugu/OneDrive/Documentos/res/output/clicko-referencia-diagnostico-2026-11-10/referencia';
const instruction=`Crie um anúncio de 18 segundos, 540x960, para Clicko, dirigido a quem já grava conteúdo mas precisa dar direção ao corte.
Use o dossiê aprovado. A hipótese é que uma transformação visível do material, ligada à prova real na timeline, tem mais força que cartelas de funcionalidades.
Pense como diretor de motion: hierarquia tipográfica, ponto de atenção estável, movimento que relaciona estados e continuidade entre elementos. Escolha a contagem de cenas e o desenho. Não use o antigo arranjo de três cartões amarelos nem apenas troque frases paradas.
O trecho de referência mostra integração de tipografia, objeto em primeiro plano e demonstração; adapte o princípio de profundidade/revelação ao produto, sem copiar a filmagem do criador. É uma folha de quadros observados; áudio da referência não avaliado.
Você tem captura REAL da timeline: um clipe vira dois perto de 3,75 s na fonte de 9 s. Há uma versão ampliada da região. Use 5 a 6 segundos contínuos da prova, desde 1,8 s até pelo menos 6,8 s da fonte, em escala que permita perceber a divisão. Não acelere ou esconda essa ação com texto. A captura é do próprio sistema, não uma interface inventada. A filmagem opcional de telefone/ring light é banco de imagem, sem endosso.
Conduza o olho de uma imagem de material bruto para uma montagem e para a prova real. Escolha uma identidade coerente com a Clicko e com as imagens, com uma cor de ênfase e contraste forte. Não distorça a interface nem prometa rosto/voz automáticos.
Copy autorizada: 'O próximo corte muda a história.' / 'Dê direção ao que você gravou.' / CTA EXATO 'Abra o Studio de Vídeo.'. Pode usar menos texto e variar sua distribuição, preservando o sentido e o CTA. O fechamento precisa de 3 s de leitura.
Não há locução neste teste. Preserve a trilha local. Texto serve à transformação, não substitui ação. Não invente métricas, preço, endosso, geração de mídia ou fala. Evite cobrir rosto, telefone ou a operação da timeline.
Antes de escolher, compare opções de encenação quanto a clareza, prova do produto e aplicação da técnica. Retorne somente a composição executável do contrato, decisões ligadas a IDs e lacunas reais. Use rectangle/ellipse, text/image, faixas e keyframes suportados; não use caminhos vetoriais ou código. Fontes cabem nos boxes em todos os estados. Captions em 540px precisam de pelo menos 24px nativos. Escalas e fades não podem esconder toda a tela. Canvas é composto acima das faixas: use captions entre faixas para profundidade. Não crie trilhas nem assets que não estão registrados.`;

async function download(url,name){const bytes=await request('GET',url,null,{bytes:true});fs.writeFileSync(path.join(root,name),bytes);return bytes;}
async function upload(bytes,title,filename,mime){
 const query=new URLSearchParams({workspace_id:lab.workspace,title,filename,media_type:mime});
 const asset=await request('POST',base+'/craft/assets?'+query,bytes,{mime,key:key+'-'+filename});
 return {id:asset.id,mediaType:mime,checksum:hash(bytes),origin:'workspace',rightsStatus:'verified'};
}
async function main(){
 await request('GET','/api/governance/auth/session');
 if((await get(base+'/bridge/session')).workspace.id!==lab.workspace)throw Error('Wrong workspace');
 if(!state.reference){state.reference=await upload(fs.readFileSync(path.join(referenceRoot,'quadros.jpg')),
   'Referência de estudo · quadros ruama / creators','reference-sheet.jpg','image/jpeg');save();}
 if(!state.assets){
  const detailId='4914bef9-219d-44b9-bf07-111e587b6d3b',rawId='7e364435-49e5-4b37-8e00-93aeaabe384f';
  const detail=await download('/api/v1/assets/'+detailId+'/content','material-timeline-ampliada.mp4');
  const raw=await download('/api/v1/assets/'+rawId+'/content','material-timeline-original.mp4');
  const audio=await download('/api/v1/assets/'+lab.assets.audio.id+'/content','trilha-fonte.wav');
  execFileSync('ffmpeg',['-nostdin','-v','error','-y','-stream_loop','-1','-i',path.join(root,'trilha-fonte.wav'),
    '-t','18','-af','afade=t=in:d=0.25,afade=t=out:st=16.8:d=1.2','-ac','2','-ar','48000',path.join(root,'trilha-18s.wav')],{windowsHide:true});
  const score=await upload(fs.readFileSync(path.join(root,'trilha-18s.wav')),'Trilha local · estudo aprofundado 18 s','score-18s.wav','audio/wav');
  state.assets=[
   {id:detailId,mediaType:'video/mp4',checksum:hash(detail),origin:'workspace',rightsStatus:'verified'},
   lab.assets.studios,
   {id:rawId,mediaType:'video/mp4',checksum:hash(raw),origin:'workspace',rightsStatus:'verified'},
   {id:'5b85f1dc-5c7a-40d7-9da7-be650f3faa1e',mediaType:'video/mp4',checksum:'fc964082f5b43dda4bb03c9517761e10ff85d598887e2975c604d7335bac1fc3',origin:'workspace',rightsStatus:'verified'},
   score];save();
 }
 if(!state.document){
  state.document=await request('POST',base+'/documents',{workspaceId:lab.workspace,contentType:'video',brandRevision:1,
   title:'Clicko · o próximo corte · direção aprofundada',brief:{objective:'Mostrar a transformação de material em montagem editável com prova real na timeline.',audience:'Criadores de anúncios que já gravam seu material',format:'video'},
   composition:{pages:[{id:'main',width:540,height:960,durationMs:18000,background:'#101010',layers:[]}],tracks:[],narrative:{experiment:{budgetUsd:1.5,effort:'xhigh',hypothesis:'visible transformation with product proof',audienceTest:false}},
    mediaTimeline:{frameRate:{numerator:24,denominator:1},durationFrames:432,tracks:[{id:'local-score',kind:'audio',clips:[{id:'score',assetId:state.assets[4].id,timeline:{startFrame:0,durationFrames:432},gainDb:-8}]}]}},assets:state.assets},{key:key+'-document'});save();
 }
 const id=state.document.documentId,materials=base+'/materials/document/'+id;
 if(!state.kit){
  state.kit=await request('PUT',materials+'/kits/deep-clicko',{expectedRevision:0,name:'Clicko · prova do corte',category:'software',goal:'explain',
   materials:state.assets.slice(0,4).map((asset,index)=>({assetId:asset.id,role:index===3?'presenter':'interface',label:['Timeline ampliada','Studio real','Timeline original','Banco de imagem · gravação'][index]}))});
  await request('PUT',materials+'/binding',{expectedRevision:0,kitId:state.kit.id,kitRevision:state.kit.revision});save();
 }
 const copyUrl=base+'/copy/document/'+id;
 if(!state.copy){
  const data={product:'Clicko: ambiente de produção e edição de vídeo com timeline editável.',audience:'Criadores de anúncios que já têm uma gravação e querem montar uma peça.',
   problem:'Gravar um arquivo não define sozinho o corte e a sequência do anúncio.',benefit:'Organizar e cortar o material numa montagem editável. Sem alegação de conversão ou autonomia total.',
   offer:'Convite para abrir o Studio de Vídeo, sem preço, prazo ou condições promocionais.',sources:'Captura real da Clicko: documento 15772c83-ba5e-43a2-860f-cb45c2a0097c mudou da revisão 1 para 2 após uma divisão a 3,75 s. Fonte: recibo e captura de 10/11/2026. Banco Pexels MART PRODUCTION 7480852 é ilustrativo.',
   objections:'Preciso ver uma ação real de edição, não uma interface fictícia ou uma promessa sem prova.',awareness:'Hipótese: conhece a gravação no celular e reconhece uma timeline, mas pode desconhecer a Clicko.',
   claims:'A Clicko permite dividir clipes e organizar a montagem. A gravação e o documento salvo demonstram essa ação. Nenhum resultado comercial é afirmado.',
   restrictions:'Sem endosso da pessoa no banco. Não prometer voz, rosto automático, mídia gerada, aumento de vendas ou tempo poupado. Referência Instagram somente como estudo de técnica.',
   angle:'Do material bruto à intenção do corte: mostrar transformação e uma operação real como prova.',hook:'O próximo corte muda a história.',
   body:'Dê direção ao que você gravou.',cta:'Abra o Studio de Vídeo.',narration:'Sem locução nesta peça. As frases serão texto de tela, acompanhadas de música local.',
   editingReference:'https://www.instagram.com/reel/DdwS-6oRvL8/ — integração de primeiro plano, tipografia e demonstração. Adaptar hierarquia e revelação ao produto; não reutilizar filmagem do criador. Áudio fora da cobertura.',
   visualPlan:'18 s vertical. Gancho com transformação visível, continuidade de um mesmo objeto, prova da divisão real durante 5–6 s sem aceleração, fechamento de pelo menos 3 s. Opus escolhe cenas, composição e transições.',
   reviewNotes:'Preparação e conferência factual operadas por Codex sob a autorização de produção. Copy não contém números nem promessas comerciais. Sem voz. A qualidade e aprovação do vídeo permanecem pendentes do usuário; aprovação deste dossiê não representa aprovação do render.'};
  const current=await get(copyUrl);
  const draft=await request('PUT',copyUrl,{expectedRevision:current.revision,requestKey:key+'-copy-draft',status:'draft',data,checks:{}});
  state.copy=await request('PUT',copyUrl,{expectedRevision:draft.revision,requestKey:key+'-copy-approved',status:'approved',data,checks:{facts:true,clear:true,credible:true,engaging:true,speakable:true}});save();
 }
 if(!state.connection){
  const connections=(await get(base+'/craft/llm-connections?workspace_id='+lab.workspace)).connections;
  const previous=connections.find(row=>row.id==='cb5c26fe-d090-4cad-99a5-50c5fb01d652');
  if(!previous)throw Error('Existing scoped Anthropic connection missing');
  state.connection=await request('PUT',base+'/craft/llm-connections/'+previous.id+'?workspace_id='+lab.workspace,
   {...previous.config,label:previous.label,provider:previous.provider,expectedRevision:previous.revision,budgetUsd:7.5,maxOutputTokens:32000});save();
 }
 fs.writeFileSync(path.join(root,'briefing.txt'),instruction);
 if(process.env.CLICKO_DEEP_PREPARE_ONLY==='1'){console.log(JSON.stringify({prepared:true,documentId:id,apiSpendUsd:0}));return;}
 if(!state.task){
  state.submissionStartedAt=new Date().toISOString();save();
  state.task=await request('POST',base+'/documents/'+id+'/agent-tasks',{expectedRevision:state.document.revision,
   instruction,planner:'editorial_experimental',editorial:{variant:'orchestrated',format:'motion',connectionId:state.connection.id,
    cutEffort:'xhigh',openEdit:true,purpose:'advertisement',references:[{assetId:state.reference.id,
      sourceUrl:'https://www.instagram.com/reel/DdwS-6oRvL8/'}]}},{key:key+'-generation',timeoutMs:740000});
  state.completedAt=new Date().toISOString();save();
 }
 if(state.task.status!=='succeeded')throw Error('Generation failed: '+state.task.errorCode+'; paid usage retained in receipt.');
 const result=state.task.result,editorial=result.editorial;
 if(editorial?.openEditing?.draftPreview?.downloadUrl)await download(editorial.openEditing.draftPreview.downloadUrl,'primeiro-corte.mp4');
 if(editorial?.preview?.downloadUrl)await download(editorial.preview.downloadUrl,'video-clicko-opus.mp4');
 if(result.commands?.length){
  const comp=result.commands.find(c=>c.id==='composition.replace')?.params.composition;
  if(comp)fs.writeFileSync(path.join(root,'proposta-editavel.json'),JSON.stringify({...state.document,composition:comp},null,2));
 }
 console.log(JSON.stringify({taskId:state.task.id,documentId:id,status:state.task.status,state:result.state,
  budgetUsd:1.5,externalCostUsd:state.task.externalCostUsd,planningTimeMs:result.planningTimeMs,
  technicalStatus:editorial?.preview?.status,modelReview:editorial?.openEditing?.modelReview,
  stageTimesMs:editorial?.openEditing?.stageTimesMs,usage:result.directionUsage},null,2));
}
main().catch(error=>{state.lastError=error.message;save();console.error(error.message);process.exitCode=1;});
