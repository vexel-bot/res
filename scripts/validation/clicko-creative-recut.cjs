/** Controlled Clicko creative-cut experiment. Re-running resumes recorded work. */
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {request, get, base, client, sleep, hash, state:lab} = require('./clicko-motion-editorial-proof.cjs');

if (!process.argv[2] || !process.argv[3]) throw Error('Provide local laboratory and a separate output directory.');
const output = path.resolve(process.argv[3]);
fs.mkdirSync(output,{recursive:true});
const scopeFile = path.join(output,'setup.json');
const setup = fs.existsSync(scopeFile) ? JSON.parse(fs.readFileSync(scopeFile)) : {};
const saveSetup = () => fs.writeFileSync(scopeFile, JSON.stringify(setup,null,2));
const proofPath = process.env.CLICKO_TIMELINE_PROOF_PATH;
const directed = Boolean(proofPath) || process.env.CLICKO_SCENE_DIRECTION==='1';
const key = (proofPath?'clicko-timeline-proof-v1-':directed?'clicko-scene-direction-v1-':'clicko-creative-recut-v1-')+lab.run;
const stock = 'artifacts/validation/sources/pexels-7480852-content-creator.mp4';
const cases = [
    {id:'motion',format:'motion',name:'Da ideia à timeline', objective:'Mostrar cenas soltas que se organizam na timeline da Clicko.',
        instruction:'Anúncio vertical de 12 s para criadores de anúncios. O problema são cenas soltas; a promessa comprovada é organizar cenas na timeline da Clicko. As formas amarelas são três cenas; a barra inferior representa a linha do tempo. Faça as três peças convergirem para a barra na ordem certa. Pode reconstruir a apresentação e o ritmo dos elementos. Evite cartelas que se limitam a trocar texto e não finja que a ilustração é uma captura do app. CTA autorizado: Abra o Studio de Vídeo. Preserve 12 s e áudio.'},
    {id:'real',format:'footage',name:'Depois do REC', objective:'Mostrar que uma gravação no celular pode virar a base de uma montagem de anúncio.',
        instruction:'Anúncio vertical de 12 s para quem já grava no celular. Mostre telefone e ring light cedo. Dê ritmo selecionando trechos reais e criando contraste de enquadramento, sem perder o telefone, sem fingir fala da pessoa, sem inventar cenas, sem endosso. O fato permitido é que você pode editar sua gravação na timeline da Clicko. Mostre o próximo passo com textos curtos e legíveis que não tapem o telefone. CTA autorizado: Abra o Studio de Vídeo. Preserve 12 s e áudio.'},
];
const timing = (startFrame,durationFrames) => ({startFrame,durationFrames});
const layer = (id,kind,x,y,width,height,zIndex,props) => ({
    id,kind,name:id,x,y,width,height,zIndex,properties:{schemaVersion:'studio.local-layer.v1',...props},
});
const shape = (id,x,y,w,h,z,fill,start=0,duration=288) =>
    layer(id,'shape',x,y,w,h,z,{shape:'rectangle',radius:12,fill,...timing(start,duration)});
function composition(brief) {
    const real = brief.id==='real';
    const layers = real ? [
        shape('tarja',24,752,492,130,3,'#141A21'),
    ] : [
        shape('base',36,560,468,140,1,'#253B53'),
        shape('cena-a',48,366,110,72,3,'#F3CA68'),
        shape('cena-b',212,295,110,72,3,'#E0A842'),
        shape('cena-c',376,393,110,72,3,'#FFE19E'),
    ];
    const texts = real ? ['Você gravou.','Agora monte o anúncio.','Abra o Studio de Vídeo.'] :
        ['Cenas soltas?','Organize na timeline.','Abra o Studio de Vídeo.'];
    for (let i=0;i<3;i++) layers.push(layer('titulo-'+i,'text',42,real?784:115,456,87,8,{
        text:texts[i],fontSize:real?31:38,align:'center',color:'#FFF6E4',...timing(i*96,96),
    }));
    const track = real ? [{id:'camera',kind:'video',muted:true,clips:[0,1,2].map(i=>({
        id:'take-'+i,assetId:proofPath&&i===1?setup.timelineProof.id:setup.stock.id,timeline:timing(i*96,96),
        source:{startMicroseconds:proofPath&&i===1?0:i*4_000_000,durationMicroseconds:4_000_000},transform:{originalAudioEnabled:false},
    }))}] : [];
    return {pages:[{id:'main',width:540,height:960,background:'#141A21',durationMs:12000,layers}],tracks:[],narrative:{},
        mediaTimeline:{frameRate:{numerator:24,denominator:1},durationFrames:288,tracks:[
            ...track,{id:'audio',kind:'audio',clips:[{id:'score',assetId:lab.assets.audio.id,timeline:timing(0,288),gainDb:-7,fadeOutFrames:12}]},
        ]}};
}

async function post(url,body,requestKey,timeoutMs) {
    let transient = 0;
    for(let attempt=0;attempt<90;attempt++){
        try {return await request('POST',url,body,{key:requestKey,timeoutMs});}
        catch(error){
            if(error.status===409 && timeoutMs && error.message.includes('agent_workspace_busy_or_interrupted_task')){
                await sleep(4000);
                continue;
            }
            if(transient++ || ![502,503,504].includes(error.status)) throw error;
            await sleep(1200);
        }
    }
    throw Error('Clicko workspace remained busy for '+url);
}
async function prepare() {
    await request('GET','/api/governance/auth/session');
    const workspace=(await get(base+'/bridge/session')).workspace.id;
    if(workspace!==lab.workspace) throw Error('Wrong workspace');
    if(!setup.stock) {
        const bytes=fs.readFileSync(stock),mediaType='video/mp4';
        const query=new URLSearchParams({workspace_id:workspace,title:'Pexels · MART PRODUCTION · 7480852',filename:path.basename(stock),media_type:mediaType});
        const uploaded=await request('POST',base+'/craft/assets?'+query,bytes,{mime:mediaType,key:key+'-stock'});
        setup.stock={id:uploaded.id,mediaType,checksum:hash(bytes),origin:'workspace',rightsStatus:'verified'};
        saveSetup();
    }
    if(proofPath&&!setup.timelineProof){
        const bytes=fs.readFileSync(proofPath), mediaType='video/mp4';
        const query=new URLSearchParams({workspace_id:workspace,title:'Clicko · divisão real na timeline',
            filename:path.basename(proofPath),media_type:mediaType});
        const uploaded=await request('POST',base+'/craft/assets?'+query,bytes,{mime:mediaType,key:key+'-proof'});
        setup.timelineProof={id:uploaded.id,mediaType,checksum:hash(bytes),origin:'workspace',rightsStatus:'verified'};
        saveSetup();
    }
    if(!setup.connection){
        const endpoint=base+'/craft/llm-connections?workspace_id='+encodeURIComponent(workspace);
        const label=proofPath?'Claude Opus 5.5 · demonstração da timeline':directed?'Claude Opus 5.5 · direção por cenas':'Claude Opus 5.5 · laboratório montagem aberta';
        const connections=(await get(endpoint)).connections;
        const existing=connections.find(row=>row.label===label&&row.provider==='anthropic');
        if(existing) setup.connection=existing.id;
        else {
            const env=require('dotenv').parse(fs.readFileSync('.env'));
            if(!env.API_CLAUDE||!env.ANTHROPIC_WORKSPACE_ID) throw Error('Missing local Anthropic configuration');
            const cfg={label,provider:'anthropic',protocol:'anthropic_messages',baseUrl:'https://api.anthropic.com/v1',authHeader:'x-api-key',authPrefix:'',
                extraHeaders:{'anthropic-workspace-id':env.ANTHROPIC_WORKSPACE_ID},models:['claude-opus-5-5'],apiKey:env.API_CLAUDE,
                enabled:true,billingMode:'metered',budgetUsd:proofPath?1.5:directed?3:6,inputUsdPerMillion:4,outputUsdPerMillion:20,maxOutputTokens:32000};
            setup.connection=(await post(endpoint,cfg,key+'-connection')).id;
        }
        saveSetup();
    }
    return workspace;
}

async function experiment(workspace,brief,mode) {
    if(proofPath) brief={...brief,instruction:brief.instruction+' Mostre a gravação real da Clicko obrigatoriamente na segunda cena. Ela é o clipe take-1. A operação é Dividir no cursor, com um clipe se tornando dois. Dê tempo para ler e entender a divisão antes de voltar ao celular. Preserve um fechamento curto e claro.'};
    const prefix=brief.id+'-'+mode;
    const target=path.join(output,prefix);
    fs.mkdirSync(target,{recursive:true});
    const file=path.join(target,'recibo.json');
    const state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{brief,mode};
    const save=()=>fs.writeFileSync(file,JSON.stringify(state,null,2));
    if(!state.source) {
        state.source=await post(base+'/documents',{workspaceId:workspace,title:brief.name+' · '+mode,contentType:'video',brandRevision:1,
            brief:{objective:brief.objective,audience:'Criadores solo de anúncios',angle:brief.name,format:'video'},
            composition:composition(brief),assets:[lab.assets.audio,...(brief.id==='real'?[setup.stock]:[]),...(proofPath?[setup.timelineProof]:[])]},key+'-doc-'+prefix);
        state.sourceHash=hash(JSON.stringify(state.source.composition));save();
    }
    const doc=base+'/documents/'+state.source.documentId;
    const video=base+'/video/documents/'+state.source.documentId;
    if(mode!=='local'&&process.env.CLICKO_CREATIVE_RESUME==='1'&&state.task&&!state.applied) {
        const result=state.task.result;
        if(directed&&state.chargedTask&&state.task.status==='failed'&&!result?.submissionStarted&&!state.recoveryPreflight) {
            state.recoveryPreflight=state.task;
            delete state.task;
            save();
        } else if(state.task.errorCode==='external_monthly_budget_exceeded'&&!result?.submissionStarted&&!state.admission) {
            state.admission=state.task;
            delete state.task;
            save();
        } else if(state.task.status==='failed'&&result?.submissionOutcome==='response_received'&&
                  (directed?result.initialSceneDirection:result.claudeRefinement)&&!state.chargedTask) {
            state.chargedTask=state.task;
            delete state.task;
            save();
        }
    }
    if(mode!=='local'&&!state.task) {
        console.log(prefix,'planning',state.source.documentId);
        state.task=await post(doc+'/agent-tasks',{expectedRevision:state.source.revision,instruction:brief.instruction,role:'audiovisual',
            planner:'editorial_experimental',editorial:{variant:'orchestrated',format:brief.format,objective:brief.objective,
                connectionId:setup.connection,cutEffort:mode,creativeCut:true,...(directed?{sceneDirection:true}:{}),
                ...(proofPath?{timelineProofAssetId:setup.timelineProof.id}:{}),
                ...(state.chargedTask ? {creativeReplayTaskId:state.chargedTask.id} : {})}},
                key+'-plan-'+prefix+(state.chargedTask?(state.recoveryPreflight?'-replay-preflight':'-replay'):state.admission?'-admitted':''),proofPath?750000:directed?510000:340000);
        save();
        console.log(prefix,'plan',state.task.status,state.task.errorCode,state.task.externalCostUsd,
            state.task.result?.editorial?.preview?.status);
    }
    if(mode!=='local'&&!state.applied) {
        const task=state.task;
        const preview=task.result?.editorial?.preview;
        if(task.status!=='succeeded'||preview?.status!=='passed_technical'||!task.result.commands?.length) {
            console.error(prefix,'blocked',JSON.stringify({error:task.errorCode,findings:preview?.findings}));
            return;
        }
        if((state.chargedTask||task).result.financialReservationUsd!==1.5) throw Error(prefix+' budget mismatch');
        const range=await get(base+'/video/library/'+preview.assetId+'/content?'+new URLSearchParams({workspaceId:workspace,clientId:client}),
            {withResponse:true,headers:{Range:'bytes=0-1023'}});
        if(range.status!==206||range.bytes.length!==1024) throw Error(prefix+' preview stream failed');
        const original=await get(doc);
        if(hash(JSON.stringify(original.composition))!==state.sourceHash) throw Error(prefix+' source changed');
        state.applied=await post(doc+'/agent-tasks/'+task.id+'/apply',{expectedRevision:state.source.revision},key+'-apply-'+prefix);save();
        const timeline=state.applied.composition.mediaTimeline;
        const audio=track=>track.kind==='audio';
        const originalTimeline=state.source.composition.mediaTimeline;
        if(JSON.stringify(timeline.tracks.filter(audio))!==JSON.stringify(originalTimeline.tracks.filter(audio))||
            timeline.durationFrames!==originalTimeline.durationFrames||JSON.stringify(state.applied.assets)!==JSON.stringify(state.source.assets))
            throw Error(prefix+' changed fixed inputs');
        fs.writeFileSync(path.join(target,'projeto-editavel.json'),JSON.stringify(state.applied,null,2));
    }
    if(!state.job) {
        state.renderStartedAt=Date.now();
        state.job=(await post(video+'/render-jobs',{expectedRevision:(state.applied||state.source).revision},key+'-render-'+prefix)).id;
        save();
    }
    const final=path.join(target,'anuncio.mp4');
    for(let attempt=0;attempt<180&&!state.render;attempt++){
        const job=await get(base+'/jobs/'+state.job);
        if(job.status==='succeeded'){
            const bytes=await get(job.result.downloadUrl,{bytes:true});
            if(hash(bytes)!==job.result.checksumSha256||job.result.durationSeconds!==12||job.result.externalCostUsd!==0)throw Error(prefix+' invalid export');
            fs.writeFileSync(final,bytes);
            const pcm=execFileSync('ffmpeg',['-nostdin','-v','error','-i',final,'-map','0:a:0','-f','s16le','pipe:1'],{maxBuffer:10*1024*1024});
            state.render={...job.result,wallSeconds:(Date.now()-state.renderStartedAt)/1000,pcmSha256:hash(pcm)};
            save();
            console.log(prefix,'render',job.id,state.render.wallSeconds);
        } else if(['failed','cancelled'].includes(job.status)) throw Error(prefix+' export '+job.errorCode);
        else await sleep(1200);
    }
    if(!state.render)throw Error(prefix+' export timed out');
}

async function main() {
    const workspace=await prepare();
    const mode=process.argv[4];
    if(proofPath&&(mode!=='high'||process.argv[5]!=='real')) throw Error('Timeline proof allows one high-effort film generation.');
    const selected=process.argv[5]?cases.filter(brief=>brief.id===process.argv[5]):cases;
    for(const brief of selected) {
        for(const variant of mode?[mode]:['local','medium','high']) {
            if(!['local','medium','high'].includes(variant)) throw Error('Invalid effort');
            await experiment(workspace,brief,variant);
        }
    }
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
