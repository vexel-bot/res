/** Reference reconstruction through the existing material-effects and render APIs. */
const fs=require('node:fs');
const path=require('node:path');
const {request,get,base,hash,sleep,state:lab}=require('./clicko-motion-editorial-proof.cjs');
if(!process.argv[2]||!process.argv[3])throw Error('Provide laboratory and separate output folder.');
const root=path.resolve(process.argv[3]);
const file=path.join(root,'recibo-reconstrucao.json');
const state=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{};
const save=()=>fs.writeFileSync(file,JSON.stringify(state,null,2));
const key='clicko-ref-depth-DdwS-6oRvL8-v1';
const reference='https://www.instagram.com/reel/DdwS-6oRvL8/';
function composition(source,matte,depth){
    const clip=id=>({id,assetId:source,timeline:{startFrame:0,durationFrames:144},
        source:{startMicroseconds:0,durationMicroseconds:6000000},transform:{originalAudioEnabled:false}});
    const caption={id:'headline',timeline:{startFrame:12,durationFrames:32},text:'TUTORIAL',
        style:{fontSize:84,fontFamily:'system',color:'#FFF0B8',outlineWidth:0,maxLines:1},
        motion:{y:-230},keyframes:[
            {property:'opacity',frame:0,value:0},{property:'opacity',frame:4,value:1,easing:'ease-out'},
            {property:'y',frame:0,value:-205},{property:'y',frame:6,value:-230,easing:'ease-out'},
        ]};
    const tracks=[{id:'background',name:'Filmagem',kind:'video',muted:true,clips:[clip('background-clip')]},
        {id:'depth-heading',name:'Título intercalado',kind:'caption',cues:[caption]}];
    if(depth)tracks.push({id:'subject',name:'Pessoa à frente do título',kind:'video',muted:true,clips:[clip('subject-clip')]},
        {id:'subject-mask',kind:'mask',targetTrackId:'subject',artifactAssetId:matte,mode:'luma'});
    tracks.push({id:'audio',kind:'audio',clips:[{id:'score',assetId:lab.assets.audio.id,timeline:{startFrame:0,durationFrames:144},gainDb:-7}]});
    return {pages:[{id:'main',width:540,height:960,durationMs:6000,background:'#141A21',layers:[]}],
        tracks:[],narrative:{referenceStudy:{url:reference,sourceExcerptSeconds:[2,8],type:'opening-depth-typography',audioAudited:false}},
        mediaTimeline:{frameRate:{numerator:24,denominator:1},durationFrames:144,tracks}};
}
async function waitJob(id){
    for(let i=0;i<500;i++){
        const job=await get(base+'/jobs/'+id);
        if(job.status==='succeeded')return job.result;
        if(['failed','cancelled'].includes(job.status))throw Error(job.errorCode+': '+job.errorMessage);
        await sleep(1200);
    }
    throw Error('Reference study timeout '+id);
}
async function main(){
    await request('GET','/api/governance/auth/session');
    if((await get(base+'/bridge/session')).workspace.id!==lab.workspace)throw Error('Wrong workspace');
    if(!state.source){
        const data=fs.readFileSync(path.join(root,'fonte-sem-titulo.mp4'));
        const query=new URLSearchParams({workspace_id:lab.workspace,title:'Estudo privado · ruama / creators · trecho 2–8 s',
            filename:'reference-study.mp4',media_type:'video/mp4'});
        const asset=await request('POST',base+'/craft/assets?'+query,data,{mime:'video/mp4',key:key+'-source'});
        state.source={id:asset.id,mediaType:'video/mp4',origin:'workspace',rightsStatus:'unknown',checksum:hash(data),
            provenance:{sourceReference:reference,usage:'reference reconstruction study',sourceInterval:[2,8]}};
        save();
    }
    if(!state.document){
        state.document=await request('POST',base+'/documents',{workspaceId:lab.workspace,contentType:'video',brandRevision:1,
            title:'Estudo · tipografia em profundidade',brief:{objective:'Reproduzir a relação pessoa/título da abertura de uma referência.',
                audience:'Revisores da Clicko',format:'video'},
            composition:composition(state.source.id,null,false),assets:[state.source,lab.assets.audio]},{key:key+'-doc'});
        save();
    }
    const materials=base+'/materials/document/'+state.document.documentId;
    if(!state.kit){
        state.kit=await request('PUT',materials+'/kits/reference-depth-study',{expectedRevision:0,name:'Estudo da referência',
            category:'other',goal:'explain',description:'Pessoa passa à frente de uma chamada grande.',
            materials:[{assetId:state.source.id,role:'presenter',label:'Trecho da referência'}]});
        const binding=(await get(materials)).binding;
        await request('PUT',materials+'/binding',{expectedRevision:binding.revision,kitId:state.kit.id,kitRevision:state.kit.revision});
        save();
    }
    if(!state.effect){
        const job=await request('POST',materials+'/effects',{expectedRevision:state.document.revision,kitRevision:state.kit.revision,
            requestKey:key+'-segment',operation:'segment_person',sourceAssetId:state.source.id,
            startSeconds:0,durationSeconds:6,preserveInteractionArea:false},{key:key+'-segment'});
        state.effect=job.id;save();
    }
    if(!state.prepared){state.prepared=await waitJob(state.effect);save();console.log('Material preparation',state.effect,state.prepared.externalCostUsd);}
    const prepared=state.prepared.preparedAssets;
    const preparedDocument=await get(base+'/documents/'+state.prepared.documentId);
    const preparedAssets=preparedDocument.assets;
    for(const variant of ['flat','depth']){
        const row=state[variant]??={};
        if(row.doc&&!row.job&&row.doc.assets.some(asset=>!asset.checksum)){
            row.originalDocument=row.doc;
            delete row.doc;
        }
        if(!row.doc){
            const assets=[prepared.source,prepared.matte].map(id=>{
                const asset=preparedAssets.find(asset=>asset.id===id);
                if(!asset?.checksum)throw Error('Prepared asset checksum missing');
                return asset;
            });
            row.doc=await request('POST',base+'/documents',{workspaceId:lab.workspace,contentType:'video',brandRevision:1,
                title:'Referência · '+variant,brief:state.document.brief,
                composition:composition(prepared.source,prepared.matte,variant==='depth'),assets:[...assets,lab.assets.audio]},
                {key:key+'-'+variant+'-doc-refs'});
            fs.writeFileSync(path.join(root,'projeto-'+variant+'.json'),JSON.stringify(row.doc,null,2));save();
        }
        if(!row.job){row.startedAt=Date.now();row.job=(await request('POST',base+'/video/documents/'+row.doc.documentId+'/render-jobs',
            {expectedRevision:row.doc.revision},{key:key+'-'+variant+'-render'})).id;save();}
        if(!row.result){
            row.result=await waitJob(row.job);
            const data=await get(row.result.downloadUrl,{bytes:true});
            if(hash(data)!==row.result.checksumSha256||row.result.externalCostUsd!==0)throw Error('Bad reference render receipt');
            fs.writeFileSync(path.join(root,'reconstrucao-'+variant+'.mp4'),data);
            row.wallSeconds=(Date.now()-row.startedAt)/1000;save();
            console.log(variant,row.wallSeconds,row.result.durationSeconds);
        }
    }
    state.externalApiCostUsd=0;
    state.reference=reference;
    save();
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
