/** One charged Claude proposal through Clicko. Replays use the original request key. */
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const dotenv=require('dotenv');
if(!process.argv[2]||!process.argv[3])throw Error('Provide the completed local lab folder and a separate output folder.');
const lab=path.resolve(process.argv[2]), out=path.resolve(process.argv[3]);
if(lab===out)throw Error('Use separate folders for the control and the Claude test.');
const {request,get,state:local,briefs,composition,constraints,origin,client,base,sleep,hash}=require('./clicko-motion-editorial-proof.cjs');
fs.mkdirSync(out,{recursive:true});
const file=path.join(out,'recibo.json');
const state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{};
const save=()=>fs.writeFileSync(file,JSON.stringify(state,null,2));
const effort=process.argv[4];
const source=effort&&process.argv[5] ? path.resolve(process.argv[5]) : null;
if(effort&&(!['medium','high'].includes(effort)||!source))throw Error('Provide medium or high effort and the original Opus output folder.');
const sourceDocument=source?JSON.parse(fs.readFileSync(path.join(source,'projeto-opus.json'))):null;
const name=effort ? 'Claude Opus 5.5 · laboratório de corte' : 'Claude Opus 5.5 · API direta';
const model='claude-opus-5-5';
const key='clicko-claude-motion-test-'+local.run+(effort?'-cut-'+effort+'-'+hash(JSON.stringify(sourceDocument.composition)).slice(0,12):'');
const instruction=effort
    ? 'Reedite o corte Bruma. Queremos que a embalagem pareça sair da fotografia e que a ação conduza até a marca, com um ritmo de anúncio vertical. Veja onde a troca parece só um corte entre cartelas. Melhore continuidade, sobreposição e contraste do produto com mudanças claras na montagem, evitando transições ornamentais. Preserve materiais, palavras, áudio e duração total.'
    : 'Refine a peça vertical de 12 segundos para comunicar a mesma embalagem saindo da fotografia. Dê hierarquia de pôster e presença ao recorte. A foto inicial ancora a identidade, o produto isolado ganha protagonismo com trajetória curta e a marca encerra estável e inteira. Use posição, escala ou opacidade com intenção distinta. Não mude materiais, palavras, intervalos, áudio ou duração.';
function assert(ok, message){if(!ok)throw Error(message);}

async function connection(workspace) {
    const endpoint=base+'/craft/llm-connections?workspace_id='+encodeURIComponent(workspace);
    const list=await get(endpoint);
    const existing=list.connections.find(row=>row.label===name&&row.provider==='anthropic');
    const env=dotenv.parse(fs.readFileSync('.env'));
    assert(env.API_CLAUDE&&/^wrkspc_[A-Za-z0-9]{16,80}$/.test(env.ANTHROPIC_WORKSPACE_ID||''),'Set API_CLAUDE and ANTHROPIC_WORKSPACE_ID in the local .env');
    if(existing){
        assert(existing.config.extraHeaders?.['anthropic-workspace-id']===env.ANTHROPIC_WORKSPACE_ID,'Existing Claude connection points at another workspace');
        assert(existing.hasCredential&&existing.config.enabled,'Existing Claude connection is disabled');
        return existing.id;
    }
    const created=await request('POST',endpoint,{label:name,provider:'anthropic',protocol:'anthropic_messages',
        baseUrl:'https://api.anthropic.com/v1',authHeader:'x-api-key',authPrefix:'',
        extraHeaders:{'anthropic-workspace-id':env.ANTHROPIC_WORKSPACE_ID},models:[model],apiKey:env.API_CLAUDE,
        enabled:true,billingMode:'metered',budgetUsd:effort?1.5:.45,inputUsdPerMillion:4,outputUsdPerMillion:20,maxOutputTokens:effort?6000:4096});
    return created.id;
}

async function main(){
    await request('GET','/api/governance/auth/session');
    const workspace=(await get(base+'/bridge/session')).workspace.id;
    assert(workspace===local.workspace,'Local comparison belongs to another workspace');
    const control=local.cases['01'].orchestrated;
    const brief=briefs.find(item=>item.id==='01');
    const id=state.connectionId||await connection(workspace);
    state.connectionId=id;save();
    if(!state.document){
        const seed=await request('POST',base+'/documents',{workspaceId:workspace,contentType:'video',brandRevision:1,
            title:'Clicko · Bruma · Motion com Claude Opus 5.5',brief:{objective:brief.objective,audience:'Criadores de anúncios e pequenos negócios',
                angle:brief.name,format:'video'},composition:sourceDocument?.composition||composition(brief),
            assets:[...new Set(brief.shots.map(row=>row[0]).concat('audio'))].map(k=>local.assets[k])},{key:key+'-doc'});
        state.document={id:seed.documentId,revision:seed.revision,seed:constraints(seed),compositionHash:hash(JSON.stringify(seed.composition))};
        assert(JSON.stringify(state.document.seed)===JSON.stringify(control.seed),'The test seed differs from the local control');
        save();
    }
    const doc=base+'/documents/'+state.document.id, video=base+'/video/documents/'+state.document.id;
    const material=base+'/materials/document/'+state.document.id;
    const kit=local.kits['01'];
    if(!state.bound){
        const binding=(await get(material)).binding;
        if(!binding.kitId)await request('PUT',material+'/binding',{expectedRevision:binding.revision,kitId:kit.id,kitRevision:kit.revision});
        else assert(binding.kitId===kit.id&&binding.kitRevision===kit.revision,'Product materials changed');
        state.bound=true;save();
    }
    if(process.env.CLICKO_CLAUDE_RETRY_BLOCKED==='1'&&state.task&&!state.applied&&
        state.task.result?.state==='blocked'&&state.task.externalCostUsd>0&&!state.blockedTasks?.length){
        state.blockedTasks=[state.task];
        delete state.task;save();
    }
    if(effort&&process.env.CLICKO_CLAUDE_RETRY_ADMISSION==='1'&&!state.admissionRejected&&
        state.task?.errorCode==='external_model_budget_exceeded'&&!state.task.result?.submissionStarted&&
        state.task.externalCostUsd===0){
        state.admissionRejected=state.task;
        delete state.task;save();
    }
    if(!state.task){
        const payload={expectedRevision:state.document.revision,instruction,role:'audiovisual',planner:'editorial_experimental',
            editorial:{variant:'orchestrated',format:'auto',objective:brief.objective,connectionId:id,...(effort?{cutEffort:effort}:{})}};
        state.task=await request('POST',doc+'/agent-tasks',payload,{key:key+'-plan'+(state.blockedTasks?.length?'-retry':'')+(state.admissionRejected?'-admitted':'')});save();
        console.log('Claude task',state.task.id,state.task.status,state.task.errorCode,state.task.externalCostUsd);
    }
    const task=state.task;
    const review=task.result?.editorial;
    assert(task.status==='succeeded'&&review?.preview?.status==='passed_technical'&&task.result.commands?.length,
        JSON.stringify({taskId:task.id,error:task.errorCode,state:task.result?.state,preview:review?.preview,cost:task.externalCostUsd}));
    assert(task.provider==='llm.anthropic'&&task.externalCostUsd>0&&review.claude.usage?.completion_tokens>0,
        'Missing metered direct Claude receipt');
    assert(review.knowledgeDigest===control.task.result.editorial.knowledgeDigest,'Knowledge version differs');
    const previewUrl=base+'/video/library/'+review.preview.assetId+'/content?'+new URLSearchParams({workspaceId:workspace,clientId:client});
    if(effort){
        const original=fs.readFileSync(path.join(source,'clicko-motion-opus-55.mp4'));
        assert(review.claude.cutEffort===effort&&review.claude.cutFrames.length>=5,'Missing render-based cut evidence');
        assert(review.claude.sourceRenderChecksum===hash(original),'The analysis render differs from the original cut');
    }
    if(!state.range){
        const range=await get(previewUrl,{withResponse:true,headers:{Range:'bytes=0-1023'}});
        assert(range.status===206&&range.bytes.length===1024&&range.headers['content-range']?.startsWith('bytes 0-1023/'),'Preview streaming range failed');
        state.range={status:range.status,contentRange:range.headers['content-range']};save();
    }
    if(!state.applied){
        const unchanged=await get(doc);
        assert(hash(JSON.stringify(unchanged.composition))===state.document.compositionHash,'Planning changed the document before review');
        const applied=await request('POST',doc+'/agent-tasks/'+task.id+'/apply',{expectedRevision:state.document.revision},{key:key+'-apply'});
        assert(JSON.stringify(constraints(applied))===JSON.stringify(control.seed),'A controlled variable changed');
        state.applied={revision:applied.revision,composition:applied.composition};
        fs.writeFileSync(path.join(out,'projeto-opus.json'),JSON.stringify(applied,null,2));save();
    }
    if(!state.job){
        const j=await request('POST',video+'/render-jobs',{expectedRevision:state.applied.revision},{key:key+'-render'});
        state.job=j.id;save();
    }
    for(let n=0;!state.render&&n<150;n++){
        const job=await get(base+'/jobs/'+state.job);
        if(job.status==='succeeded'){
            const bytes=await get(job.result.downloadUrl,{bytes:true});
            assert(hash(bytes)===job.result.checksumSha256&&job.result.externalCostUsd===0,'Invalid final render');
            fs.writeFileSync(path.join(out,'clicko-motion-opus-55.mp4'),bytes);
            state.render=job.result;save();break;
        }
        assert(!['failed','cancelled'].includes(job.status),job.errorMessage||'Render failed');
        await sleep(1500);
    }
    assert(state.render,'The final render did not complete in time');
    const final=path.join(out,'clicko-motion-opus-55.mp4');
    const localVideo=path.join(lab,control.renderResult.file);
    fs.copyFileSync(localVideo,path.join(out,'clicko-motion-local.mp4'));
    const pcm=videoPath=>hash(execFileSync('ffmpeg',['-nostdin','-v','error','-i',videoPath,'-map','0:a:0','-f','s16le','pipe:1'],{maxBuffer:10*1024*1024}));
    const audioIdentical=pcm(final)===pcm(localVideo);
    assert(audioIdentical,'Decoded audio differed from the local control');
    assert(state.render.durationSeconds===control.renderResult.durationSeconds,'Render duration differs');
    if(source) {
        const original=path.join(source,'clicko-motion-opus-55.mp4');
        assert(pcm(final)===pcm(original),'Audio changed compared with the original cut');
        fs.copyFileSync(original,path.join(out,'corte-opus-anterior.mp4'));
    }
    const usage=review.claude.usage;
    const blockedCost=(state.blockedTasks||[]).reduce((sum, attempt)=>sum+attempt.externalCostUsd,0);
    const total=Number((task.externalCostUsd+blockedCost).toFixed(8));
    state.cost={successfulProposalUsd:task.externalCostUsd,blockedProposalsUsd:blockedCost,totalUsd:total};
    save();
    const report=[
        '# Clicko · Opus 5.5 direto versus orquestrador local','',
        effort ? 'Mesmo brief Bruma, materiais, texto, duração e áudio. O Opus recebeu quadros do corte anterior, incluindo transições, e propôs mudanças na montagem. A Clicko aplicou e renderizou o projeto editável. Esforço: '+effort+'.'
            : 'Mesmo brief, kit Bruma, fotos, copy, áudio e duração de 12 segundos. O mesmo orquestrador preparou ambos os cortes. No braço Claude, o Opus recebeu três amostras dos materiais e propôs ajustes em camadas existentes antes da prévia técnica. A Clicko validou e renderizou o resultado. O áudio decodificado é idêntico.','',
        '[Versão Opus](clicko-motion-opus-55.mp4) · [Versão local](clicko-motion-local.mp4) · [Recibo](recibo.json)','',
        'Ajustes propostos pelo modelo: '+task.result.rationale,'',
        '| Item | Local | Claude direto |','|---|---:|---:|',
        '| Custo de API | US$ 0 | US$ '+task.externalCostUsd+' |',
        '| Tokens de entrada | 0 | '+usage.prompt_tokens+' |',
        '| Tokens de saída | 0 | '+usage.completion_tokens+' |',
        '| Tempo de planejamento e prévia | '+(control.task.result.planningTimeMs/1000).toFixed(2)+' s | '+(task.result.planningTimeMs/1000).toFixed(2)+' s |',
        '| Revisão técnica | passou | passou |','',
        'Custo total, incluindo propostas bloqueadas: US$ '+total+'.','',
        'Custo calculado a partir do uso retornado pela Anthropic e da tarifa pública do modelo. [Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview)','',
        'O streaming autenticado respondeu HTTP 206 ao pedido parcial da prévia. Este é um teste de um brief. A preferência do público permanece em aberto.',''
    ].join('\n');
    fs.writeFileSync(path.join(out,'comparacao.md'),report);
    console.log(JSON.stringify({cost:state.cost,usage,audioIdentical,previewRange:state.range,documentId:state.document.id,renderId:state.job}));
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
