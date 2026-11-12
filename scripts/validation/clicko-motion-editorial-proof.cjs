/**
 * Six paired Clicko briefs, three local planners per brief. Requires the
 * existing local development studio and the previously produced local assets.
 * Run from the repository: node scripts/validation/clicko-motion-editorial-proof.cjs <output-directory>
 */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const out = path.resolve(process.argv[2] || 'output/motion-editorial-proof');
const base = '/api/v1/studios/v1';
const origin = 'http://127.0.0.1:3000';
const client = process.env.CLICKO_VIDEO_CLIENT_ID || 'client-ws-dev-clicko';
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const stateFile = path.join(out, 'receipts.json');
fs.mkdirSync(out, {recursive:true});
const state = fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, 'utf8')) :
    {run:crypto.randomUUID(), assets:{}, kits:{}, cases:{}, apiCalls:0, externalCostUsd:0};
const save = () => fs.writeFileSync(stateFile, JSON.stringify(state, null, 2));
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const equal = (a,b) => JSON.stringify(a) === JSON.stringify(b);
const assert = (valid, reason) => { if (!valid) throw Error(reason); };
let cookie = '';

function request(method, url, body, opts={}) {
    const data = body == null ? null : opts.mime ? body : Buffer.from(JSON.stringify(body));
    return new Promise((resolve,reject) => {
        const headers = {Cookie:cookie,Origin:origin,'x-clicko-studio-module':'create-video','x-clicko-client-id':client,
            'Idempotency-Key':opts.key || crypto.randomUUID(),...opts.headers};
        if(data) Object.assign(headers,{'Content-Type':opts.mime || 'application/json','Content-Length':data.length});
        const req = http.request(origin+url,{method,headers,agent:false},response=>{
            if(response.headers['set-cookie']) cookie=response.headers['set-cookie'][0].split(';')[0];
            const chunks=[];
            response.on('data', chunk=>chunks.push(chunk));
            response.on('end',()=>{
                const bytes=Buffer.concat(chunks);
                if(response.statusCode>=300) {
                    const error=Error(method+' '+url+' '+response.statusCode+' '+bytes.toString().slice(0,1000));
                    error.status=response.statusCode;reject(error);return;
                }
                if(opts.withResponse) resolve({status:response.statusCode, headers:response.headers, bytes});
                else if(opts.bytes) resolve(bytes);
                else try {resolve(JSON.parse(bytes.toString()));} catch(error){reject(error);}
            });
        });
        req.setTimeout(opts.timeoutMs || 240000,()=>req.destroy(Object.assign(Error('Local request timeout'),{code:'ETIMEDOUT'})));
        req.on('error',reject);
        req.end(data);
    });
}
async function get(url,opts={}) {
    for(let attempt=0;attempt<8;attempt++){
        try {return await request('GET',url,null,opts);}
        catch(error) {
            if(error.status===401) await request('GET','/api/governance/auth/session');
            else if(![502,503,504].includes(error.status)&&!['ECONNRESET','ECONNREFUSED','ETIMEDOUT'].includes(error.code)) throw error;
            await sleep(1500);
        }
    }
    throw Error('Local GET retries exhausted: '+url);
}
const coffee = '.codex-runtime/two-ads-20261108/';
const integrated = '.codex-runtime/video-integrado-20261107/';
const initial = '.codex-runtime/video-openrouter-20261107/';
const files = {
    coffee: [coffee+'product.jpg','image/jpeg'],
    bag: [coffee+'reel-cutout.png','image/png'],
    logo: [coffee+'bruma.png','image/png'],
    lift: [coffee+'scene.mp4','video/mp4'],
    pour: [coffee+'use.mp4','video/mp4'],
    sketch: [integrated+'source1.png','image/png'],
    order: [integrated+'source2.png','image/png'],
    decide: [integrated+'scene1.mp4','video/mp4'],
    arrange: [integrated+'scene2.mp4','video/mp4'],
    dashboard: [initial+'dashboard.png','image/png'],
    calendar: [initial+'calendar.png','image/png'],
    studios: [initial+'studios.png','image/png'],
    audio: [coffee+'score.wav','audio/wav']
};
const briefs = [
    {id:'01', name:'Foto para recorte', goal:'showcase', category:'physical', format:'motion',
        objective:'Mostrar que a embalagem mantém sua identidade ao sair da fotografia e ganhar destaque.',
        texts:['A foto apresenta.','O recorte destaca.','Veja o produto.'],
        shots:[['coffee','product',0,4],['bag','product_cutout',4,8],['logo','logo',8,12]],
        key:['O mesmo pacote verde aparece na foto e como recorte','A mudança isola o produto, preservando seu rótulo']},
    {id:'02', name:'Mensagem antes das cenas', goal:'explain', category:'other', format:'motion',
        objective:'Explicar como uma escolha de mensagem determina a ordem dos materiais.',
        texts:['Escolha uma ideia.','Organize a sequência.','Revise a montagem.'],
        shots:[['sketch','state_before',0,4],['order','state_after',4,12]],
        key:['Há uma escolha inicial','A escolha orienta a organização dos materiais']},
    {id:'03', name:'Embalagem até a xícara', goal:'demonstrate', category:'physical', format:'hybrid',
        objective:'Apresentar o pacote na foto e mostrar seu contexto de uso em cenas de manuseio e café servido.',
        texts:['Veja o produto.','Observe o gesto.','Café na xícara.'],
        shots:[['coffee','product',0,4],['lift','presenter',4,8,1.1],['pour','demo',8,12]],
        key:['A foto apresenta a embalagem','O vídeo mostra alguém manuseando e servindo café']},
    {id:'04', name:'Escolha no papel', goal:'explain', category:'service', format:'hybrid',
        objective:'Mostrar uma decisão visual e sua consequência na organização dos quadros.',
        texts:['Um ponto de partida.','Escolha o caminho.','Organize os quadros.'],
        shots:[['sketch','product',0,4],['decide','presenter',4,8,1.6],['arrange','demo',8,12,1]],
        key:['Os materiais começam dispersos','Uma pessoa escolhe e organiza os quadros']},
    {id:'05', name:'Demonstração por gesto', goal:'demonstrate', category:'service', format:'footage',
        objective:'Acompanhar com filmagem a seleção e organização física, sem interromper a ação com cartelas.',
        texts:['Compare as opções.','Escolha e organize.','Confira a sequência.'],
        shots:[['decide','presenter',0,6,1],['arrange','demo',6,12,1]],
        key:['A pessoa compara os papéis','A sequência é organizada pelas mãos']},
    {id:'06', name:'Percurso pela Clicko', goal:'demonstrate', category:'software', format:'interface',
        objective:'Identificar o painel da Clicko, localizar o calendário e reconhecer a área de estúdios a partir de capturas reais.',
        texts:['Visão do projeto.','Abra o calendário.','Encontre os estúdios.'],
        shots:[['dashboard','interface',0,4],['calendar','interface',4,8],['studios','interface',8,12]],
        key:['O vídeo apresenta a interface da Clicko','O caminho passa por painel, calendário e estúdios']}
];
const startFrame = t => Math.round(t*24);
const span = (from,to) => ({startFrame:startFrame(from),durationFrames:startFrame(to)-startFrame(from)});
const mediaPath = id => base+'/video/documents/'+id;
const docPath = id => base+'/documents/'+id;
const materialsPath = id => base+'/materials/document/'+id;
const modes = ['baseline','knowledge','orchestrated'];

async function upload(key) {
    if(state.assets[key]) return state.assets[key];
    const [filename,mime]=files[key];
    const q=new URLSearchParams({workspace_id:state.workspace,title:'Prova editorial · '+key,
        filename:path.basename(filename),media_type:mime});
    const bytes=fs.readFileSync(filename);
    const uploaded=await request('POST',base+'/craft/assets?'+q,bytes,{mime,key:state.run+'-asset-'+key});
    state.assets[key]={id:uploaded.id,mediaType:mime,checksum:hash(bytes),origin:'workspace',rightsStatus:'unknown'};
    save();return state.assets[key];
}
function layer(id, kind, x, y, width, height, zIndex, properties) {
    return {id,kind,name:id,x,y,width,height,zIndex,properties:{schemaVersion:'studio.local-layer.v1',...properties}};
}
function composition(brief) {
    const isInterface=brief.format==='interface';
    const width=isInterface?800:540, height=isInterface?450:960;
    const layers=[], footage=[];
    for (let index=0;index<brief.shots.length;index++) {
        const [key, ,from,to,offset]=brief.shots[index], asset=state.assets[key];
        const timing=span(from,to);
        if(asset.mediaType.startsWith('video/')){
            footage.push({id:'shot-'+index,assetId:asset.id,timeline:timing,
                source:{startMicroseconds:Math.round((offset||0)*1e6),durationMicroseconds:(to-from)*1e6},
                transform:{originalAudioEnabled:false}});
        } else {
            layers.push(layer('visual-'+index,'image',width*.11,height*.27,width*.78,height*.46,1,
                {assetId:asset.id,...timing}));
        }
    }
    for(let index=0;index<brief.texts.length;index++){
        const timing=span(index*4,(index+1)*4);
        layers.push(layer('texto-'+index,'text',width*.10,height*.12,width*.79,110,5,
            {text:brief.texts[index],fontSize:isInterface?34:39,fontWeight:700,color:'#F9F0DF',...timing}));
    }
    const timeline={schemaVersion:'studio.media-timeline.v1',frameRate:{numerator:24,denominator:1},durationFrames:288,
        tracks:[...(footage.length?[{id:'media',kind:'video',clips:footage}]:[]),
            {id:'som',kind:'audio',clips:[{id:'musica',assetId:state.assets.audio.id,timeline:span(0,12),gainDb:-3,fadeOutFrames:8}]}]};
    return {pages:[{id:'main',width,height,safeArea:28,background:'#142622',durationMs:12000,layers}],
        narrative:{videoStudio:{engine:'filmcraft',kind:'social',locale:'pt-BR'}},tracks:[],mediaTimeline:timeline};
}
const constraints = document => ({
    width:document.composition.pages[0].width, height:document.composition.pages[0].height,
    assets:document.assets.map(x=>[x.id,x.checksum]).sort(),
    text:document.composition.pages[0].layers.filter(x=>x.kind==='text').map(x=>[x.id,x.properties.text]).sort(),
    fps:document.composition.mediaTimeline.frameRate, duration:document.composition.mediaTimeline.durationFrames,
    audio:document.composition.mediaTimeline.tracks.filter(x=>x.kind==='audio'),
    media:document.composition.mediaTimeline.tracks.filter(x=>x.kind==='video'||x.kind==='overlay')
        .flatMap(x=>x.clips.map(c=>[c.assetId,c.source?.startMicroseconds,c.source?.durationMicroseconds])).sort()
});
async function prepare(brief,variant) {
    const entry=state.cases[brief.id]??={};
    const row=entry[variant]??={};
    const keys=[...new Set(brief.shots.map(s=>s[0]).concat('audio'))];
    for(const key of keys) await upload(key);
    if(!row.documentId){
        const created=await request('POST',base+'/documents',{workspaceId:state.workspace,contentType:'video',
            title:'Prova '+brief.id+' · '+brief.name+' · '+variant,brandRevision:1,
            brief:{objective:brief.objective,audience:'Criadores de anúncios e pequenos negócios',angle:brief.name,format:'video'},
            composition:composition(brief),assets:keys.map(k=>state.assets[k])},
        {key:state.run+'-doc-'+brief.id+'-'+variant+(row.refinement?'-'+row.refinement:'')});
        row.documentId=created.documentId;row.sourceRevision=created.revision;
        row.seed=constraints(created);row.seedHash=hash(JSON.stringify(created.composition));save();
    }
    const kitName='motion-proof-'+state.run.slice(0,8)+'-'+brief.id;
    const endpoint=materialsPath(row.documentId);
    if(!state.kits[brief.id]){
        state.kits[brief.id]=await request('PUT',endpoint+'/kits/'+kitName,{expectedRevision:0,name:'Kit · '+brief.name,
            category:brief.category,goal:brief.goal,description:brief.objective,visualIdentity:'Pinho e marfim',
            materials:brief.shots.map(([key,role])=>({assetId:state.assets[key].id,role,label:key,alignmentGroup:brief.id}))});
        save();
    }
    if(!row.bound){
        const binding=(await get(endpoint)).binding;
        assert(!binding?.kitId||binding.kitId===kitName,'Kit diferente já está vinculado');
        if(!binding?.kitId)await request('PUT',endpoint+'/binding',{expectedRevision:binding?.revision||0,kitId:kitName,kitRevision:state.kits[brief.id].revision});
        row.bound=true;save();
    }
    return row;
}
const instruction = 'Suavize a transição dos títulos e organize o ritmo para que a mudança fique clara.';
async function plan(brief,variant,row) {
    if(process.env.CLICKO_MOTION_RETRY_FAILED==='1'&&row.task?.status==='failed'&&!row.appliedRevision){
        (row.failedTasks??=[]).push(row.task);
        delete row.task;save();
    }
    if(row.task)return;
    const current=await get(docPath(row.documentId));
    assert(hash(JSON.stringify(current.composition))===row.seedHash,'Documento de origem já alterado');
    const body={expectedRevision:row.sourceRevision,instruction,role:'audiovisual',
        ...(variant==='baseline' ? {planner:'deterministic'} :
            {planner:'editorial_experimental',editorial:{variant,format:'auto',objective:brief.objective}})};
    const key=state.run+'-plan-'+brief.id+'-'+variant+(row.refinement?'-'+row.refinement:'')+(row.failedTasks?.length?'-retry-'+row.failedTasks.length:'');
    let task=await request('POST',docPath(row.documentId)+'/agent-tasks',body,{key});
    for(let attempt=0; ['queued','running'].includes(task.status)&&attempt<150;attempt++){
        await sleep(1500);task=await get(docPath(row.documentId)+'/agent-tasks/'+task.id);
    }
    row.task=task;save();
    assert(task.status==='succeeded',JSON.stringify({brief:brief.id,variant,error:task.errorCode,state:task.result?.state,editorial:task.result?.editorial}));
    assert(task.externalCostUsd===0,'Planner charged');
    if(variant!=='baseline'){
        const editorial=task.result?.editorial;
        assert(editorial?.format===brief.format, 'Formato inesperado: '+brief.id+' '+editorial?.format);
        assert(editorial.cardIds?.length>0, 'A proposta não consultou fichas');
        if(variant==='orchestrated'){
            assert(editorial.preview?.status==='passed_technical','Prévia sem validação técnica: '+brief.id);
            assert(editorial.repairCount<=1,'A proposta excedeu a revisão localizada');
        }
    }
    assert(hash(JSON.stringify((await get(docPath(row.documentId))).composition))===row.seedHash,'Planejamento alterou o original');
    if(!state.replay){
        const replay=await request('POST',docPath(row.documentId)+'/agent-tasks',body,{key});
        assert(replay.id===task.id,'Replay criou outra tarefa');
        state.replay=true;save();
    }
}
async function apply(brief,variant,row) {
    if(row.appliedRevision)return;
    const task=row.task;
    assert(task.status==='succeeded'&&task.result?.commands?.length,'A proposta não pode ser aplicada: '+brief.id+' '+variant);
    const updated=await request('POST',docPath(row.documentId)+'/agent-tasks/'+task.id+'/apply',
        {expectedRevision:row.sourceRevision},{key:state.run+'-apply-'+brief.id+'-'+variant});
    assert(equal(constraints(updated),row.seed),'Uma variável controlada mudou: '+brief.id+' '+variant);
    row.appliedRevision=updated.revision;
    row.compositionHash=hash(JSON.stringify(updated.composition));save();
    if(!state.staleCheck){
        try{
            await request('POST',docPath(row.documentId)+'/agent-tasks',
                {expectedRevision:row.sourceRevision,instruction,role:'audiovisual',planner:'deterministic'},{key:state.run+'-stale'});
            throw Error('O planner aceitou revisão desatualizada');
        }catch(error){assert(error.status===409,String(error));}
        state.staleCheck=true;save();
    }
}
async function render(brief,variant,row) {
    const directory=path.join(out,'renderizados',brief.id);
    fs.mkdirSync(directory,{recursive:true});
    const filename=path.join(directory,variant+'.mp4');
    if(row.renderResult&&fs.existsSync(filename))return;
    if(!row.jobId){
        const j=await request('POST',mediaPath(row.documentId)+'/render-jobs',
            {expectedRevision:row.appliedRevision},{key:state.run+'-render-'+brief.id+'-'+variant+(row.refinement?'-'+row.refinement:'')});
        row.jobId=j.id;save();
    }
    for(let i=0;i<250;i++){
        const job=await get(base+'/jobs/'+row.jobId);
        if(job.status==='succeeded'){
            fs.writeFileSync(filename,await get(job.result.downloadUrl,{bytes:true}));
            const info=JSON.parse(execFileSync('ffprobe',['-v','error','-show_format','-show_streams','-of','json',filename]));
            const video=info.streams.find(s=>s.codec_type==='video');
            const audio=info.streams.find(s=>s.codec_type==='audio');
            assert(video&&audio&&video.avg_frame_rate==='24/1'&&Number(video.nb_frames)===288,'Export inválido');
            row.renderResult={...job.result,file:path.relative(out,filename),fileHash:hash(fs.readFileSync(filename)),
                frames:Number(video.nb_frames),size:[video.width,video.height],durationSeconds:Number(info.format.duration)};
            save();
            fs.writeFileSync(path.join(directory,variant+'-projeto.json'),JSON.stringify(await get(docPath(row.documentId)),null,2));
            console.log(brief.id,variant,row.jobId,row.renderResult.frames);return;
        }
        if(['failed','cancelled'].includes(job.status))throw Error(JSON.stringify({brief:brief.id,variant,job:job.id,error:job.errorMessage}));
        await sleep(1500);
    }
    throw Error('Local render wait timed out: '+row.jobId);
}
function preserveBeforeRefinement(brief,variant,refinement) {
    const entry=state.cases[brief.id], row=entry?.[variant];
    if(variant==='baseline'||row?.refinement===refinement)return;
    assert(row?.renderResult?.file,'É preciso ter uma exportação anterior para comparar');
    const previousDir=path.join(out,'antes-da-correcao',brief.id);
    fs.mkdirSync(previousDir,{recursive:true});
    const oldFile=path.join(out,row.renderResult.file);
    const archive=path.join(previousDir,variant+'.mp4');
    fs.copyFileSync(oldFile,archive);
    fs.copyFileSync(path.join(path.dirname(oldFile),variant+'-projeto.json'),path.join(previousDir,variant+'-projeto.json'));
    row.renderResult.file=path.relative(out,archive);
    (state.refined??={})[brief.id+'-'+variant]=row;
    entry[variant]={refinement};save();
}
async function main(){
    await request('GET','/api/governance/auth/session');
    const session=await get(base+'/bridge/session');
    assert(!state.workspace||state.workspace===session.workspace.id,'Workspace changed');
    state.workspace=session.workspace.id;save();
    fs.writeFileSync(path.join(out,'briefs-e-gabaritos.json'),JSON.stringify(briefs,null,2));
    const selected=process.env.CLICKO_MOTION_BRIEF;
    const selectedMode=process.env.CLICKO_MOTION_VARIANT;
    const refinement=process.env.CLICKO_MOTION_REFINE;
    assert(!selectedMode||modes.includes(selectedMode),'Unknown proof variant');
    assert(!refinement||(selected&&refinement==='fit-proof'),'Select one brief for the refinement');
    for(const brief of briefs.filter(b=>!selected||b.id===selected)){
        for(const variant of modes.filter(v=>!selectedMode||v===selectedMode)){
            if(refinement)preserveBeforeRefinement(brief,variant,refinement);
            const row=await prepare(brief,variant);
            if(process.env.CLICKO_MOTION_PREPARE==='1')continue;
            await plan(brief,variant,row);
            await apply(brief,variant,row);
            await render(brief,variant,row);
        }
        const variants=Object.values(state.cases[brief.id]);
        assert(variants.every(x=>equal(x.seed,variants[0].seed)),'Os braços não compartilharam as mesmas variáveis');
    }
}
module.exports={request,get,state,briefs,composition,constraints,origin,client,base,sleep,hash};
if(require.main===module)main().catch(error=>{console.error(error.message);process.exitCode=1;});
