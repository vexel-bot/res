/** Recompile the same paid direction after localized, free presentation fixes. */
const fs = require('node:fs');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {request,get,base,hash,sleep,state:lab} = require('./clicko-motion-editorial-proof.cjs');
const root=path.resolve(process.argv[3]||'');
if(!process.argv[2]||!process.argv[3])throw Error('Provide local laboratory and timeline-proof output.');
const file=path.join(root,'revisao-local.json');
const state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{};
const save=()=>fs.writeFileSync(file,JSON.stringify(state,null,2));
const source=JSON.parse(fs.readFileSync(path.join(root,'real-high','recibo.json')));
const key='clicko-timeline-proof-local-revision-'+source.task.id;
async function main(){
    await request('GET','/api/governance/auth/session');
    if(!state.asset){
        const bytes=fs.readFileSync(path.join(root,'timeline-clicko-ampliada.mp4'));
        const query=new URLSearchParams({workspace_id:lab.workspace,title:'Clicko · detalhe ampliado da divisão',
            filename:'timeline-clicko-ampliada.mp4',media_type:'video/mp4'});
        const asset=await request('POST',base+'/craft/assets?'+query,bytes,{mime:'video/mp4',key:key+'-upload'});
        state.asset={id:asset.id,mediaType:'video/mp4',checksum:hash(bytes),origin:'workspace',rightsStatus:'verified'};
        save();
    }
    if(!state.document){
        const document=structuredClone(source.applied);
        const timeline=document.composition.mediaTimeline;
        const oldAsset=timeline.tracks.find(t=>t.kind==='video').clips[1].assetId;
        for(const clip of timeline.tracks.find(t=>t.kind==='video').clips)if(clip.assetId===oldAsset)clip.assetId=state.asset.id;
        document.assets=document.assets.map(asset=>asset.id===oldAsset?state.asset:asset);
        state.document=await request('POST',base+'/documents',{
            workspaceId:lab.workspace,contentType:'video',brandRevision:1,title:'Depois do REC · edição real · revisão local',
            brief:document.brief,composition:document.composition,assets:document.assets,
        },{key:key+'-document'});
        state.paidTaskId=source.task.id;
        state.costUsd=source.task.externalCostUsd;
        state.repairApiCostUsd=0;
        fs.writeFileSync(path.join(root,'projeto-final.json'),JSON.stringify(state.document,null,2));
        save();
    }
    if(!state.job){
        state.startedAt=Date.now();
        state.job=(await request('POST',base+'/video/documents/'+state.document.documentId+'/render-jobs',
            {expectedRevision:state.document.revision},{key:key+'-render'})).id;
        save();
    }
    for(let i=0;i<120&&!state.render;i++){
        const job=await get(base+'/jobs/'+state.job);
        if(job.status==='succeeded'){
            const bytes=await get(job.result.downloadUrl,{bytes:true});
            if(job.result.externalCostUsd!==0||job.result.durationSeconds!==12||hash(bytes)!==job.result.checksumSha256)
                throw Error('Invalid repaired timeline export');
            const final=path.join(root,'anuncio-timeline-clicko.mp4');
            fs.writeFileSync(final,bytes);
            const pcm=execFileSync('ffmpeg',['-nostdin','-v','error','-i',final,'-map','0:a:0','-f','s16le','pipe:1'],
                {maxBuffer:10*1024*1024});
            if(hash(pcm)!==source.render.pcmSha256)throw Error('Audio changed during local repair');
            state.render={...job.result,wallSeconds:(Date.now()-state.startedAt)/1000,pcmSha256:hash(pcm)};
            save();
            console.log(JSON.stringify({cost:state.costUsd,localRepairUsd:0,exportSeconds:state.render.wallSeconds,file:final}));
        }else if(['failed','cancelled'].includes(job.status))throw Error(job.errorCode);
        else await sleep(1000);
    }
    if(!state.render)throw Error('Local repair render timed out');
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
