/** Live deterministic acceptance through KLIC's real conversation router and
 * signed Studios bridge, only against the isolated dev:local profile.
 * No browser session/license bypass and no mock backend/model inference.
 * Run: node --import tsx scripts/agents/stage2-live.ts
 */
import assert from 'node:assert/strict';
import express from 'express';
import { randomUUID } from 'node:crypto';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { createGovernanceRouter } from '../../server/governance';
import { createKlicRuntime } from '../../server/klic/router';
import { ConversationStore } from '../../server/klic/conversations';
import { KlicMemory } from '../../server/klic/store';
import { createStudiosProxy } from '../../server/studios/proxy';

const root=path.resolve(import.meta.dirname,'../..');
const profile=path.join(root,'.codex-runtime/stage1-local');
const stage3=process.argv.includes('--stage3');
const output=path.join(root,stage3 ? '.codex-runtime/stage3-validation' : process.argv.includes('--review') ? '.codex-runtime/step2-review-validation' : '.codex-runtime/step2-validation');
const controlStatus=execFileSync(process.execPath,['scripts/dev-local.mjs','status'],{cwd:root,encoding:'utf8'}).trim();
assert.ok(controlStatus.startsWith('{'),'The isolated local profile is starting or unavailable; wait for ready before QA.');
const status=JSON.parse(controlStatus);
assert.equal(path.resolve(status.dataDirectory),profile,'Only the isolated QA profile is allowed.');
assert.equal(status.ready,true);
process.env.NODE_ENV='test'; // Isolated in-process governance fixture; not the running platform.
process.env.CLICKO_STUDIOS_ORIGIN='http://127.0.0.1:8018';
process.env.CLICKO_STUDIOS_BRIDGE_SECRET=readFileSync(path.join(profile,'bridge-key'),'utf8').trim();
mkdirSync(output,{recursive:true});
const run=randomUUID();
const headers={'Content-Type':'application/json','x-workspace-id':'ws-1','x-user-id':'usr-master'};
let remoteProviderCalls=0;
const app=express();
app.use(['/governance','/api/klic'],express.json());
app.use('/governance',createGovernanceRouter({dataFile:null}));
const conversations=new ConversationStore(path.join(output,'conversation-fixture-'+run));
const runtime=createKlicRuntime({memory:new KlicMemory(null),conversations,conversationProvider:{
    async *stream(){remoteProviderCalls++;throw new Error('Paid/model route forbidden for this QA.');yield '';},
    async transcribe(){remoteProviderCalls++;throw new Error('Transcription forbidden for this QA.');},
}});
app.use('/api/klic',runtime.router);
app.use(['/api/v1/studios/v1','/api/v1/assets'],createStudiosProxy({origin:'http://127.0.0.1:8018'}));
const server=app.listen(0,'127.0.0.1');
await new Promise<void>(resolve=>server.once('listening',resolve));
const origin=`http://127.0.0.1:${(server.address() as {port:number}).port}`;
// Governance seed identities exist only in this fixture; projects go to the
// isolated QA database, not production. The normal bridge checks stay enabled.
async function post(route:string,body:unknown,extra:Record<string,string>={}) {
    const response=await fetch(origin+route,{method:'POST',headers:{...headers,...extra},body:JSON.stringify(body)});
    assert.ok(response.ok,`${route}: ${response.status} ${await response.clone().text()}`);
    return response;
}
async function get(route:string,module='create-video') {
    const response=await fetch(origin+route,{headers:{...headers,'x-clicko-studio-module':module}});
    assert.ok(response.ok,`${route}: ${response.status}`);
    return response;
}
function persist(name:string,value:unknown){writeFileSync(path.join(output,name),JSON.stringify(value,null,2));}
const moduleHeaders={'x-clicko-studio-module':'create-video','Idempotency-Key':run};
try {
    const conversation=await (await post('/api/klic/conversations/create',{workspaceId:'ws-1',clientId:null,source:'ai-chat'})).json();
    const requestId=randomUUID();
    const input={conversationId:conversation.id,workspaceId:'ws-1',clientId:null,source:'ai-chat',requestId,
        actionId:'mode.local-production',message:'Crie um motion design de 15 segundos sobre tecnologia e inovação, com três cenas, textos animados, cartões gráficos e transições suaves.'};
    const events=(await (await post('/api/klic/conversations/send',input)).text()).trim().split('\n').map(line=>JSON.parse(line));
    const completed=events.find(event=>event.type==='done');
    assert.ok(completed,JSON.stringify(events));
    const answer=completed.data.messages.at(-1);
    assert.match(answer.content,/sem inferência/);
    const {documentId,taskId}=answer.production;
    const base=`/api/v1/studios/v1/documents/${documentId}`;
    const task=await (await get(base+`/agent-tasks/${taskId}`)).json();
    assert.deepEqual(task.result.delegations,['audiovisual','image']);
    assert.equal(task.result.inference,'none');
    assert.equal(task.externalCostUsd,0);
    let doc=await (await post(base+`/agent-tasks/${taskId}/apply`,{expectedRevision:task.documentRevision},moduleHeaders)).json();
    assert.equal(doc.composition.mediaTimeline.durationFrames,360);
    assert.equal(doc.composition.narrative.localProduction.scenes.length,3);
    // Explicit QA editing step: keep the project and every layer editable, but
    // use 640x360 for a short CPU render on the audited 8-GB integrated-GPU host.
    const composition=structuredClone(doc.composition), page=composition.pages[0];
    const factor=640/page.width;
    page.width=640;page.height=360;
    for(const layer of page.layers) {
        for(const property of ['x','y','width','height']) layer[property]*=factor;
        if(layer.properties.fontSize)layer.properties.fontSize=Math.round(layer.properties.fontSize*factor);
        if(layer.properties.radius)layer.properties.radius=Math.round(layer.properties.radius*factor);
        for(const key of layer.properties.keyframes || []) if(['x','y'].includes(key.property))key.value*=factor;
    }
    doc=await (await post(base+'/local-commands',{expectedRevision:doc.revision,
        commands:[{id:'composition.replace',params:{composition}}]},moduleHeaders)).json();
    persist('klic-creation.json',{requestId,conversationId:conversation.id,answer,task});
    console.log(JSON.stringify({phase:'klic-plan-applied',documentId,taskId,inference:'none'}));
    async function command(instruction:string,selectedLayerIds:string[]=[],apply=true) {
        const events=(await (await post('/api/klic/conversations/send',{...input,requestId:randomUUID(),message:instruction,
            productionContext:{module:'create-video',selected:{kind:'studio-document',id:documentId},selectedLayerIds}})).text()).trim().split('\n').map(line=>JSON.parse(line));
        const answer=events.find(event=>event.type==='done')?.data.messages.at(-1);
        assert.ok(answer,JSON.stringify(events));
        const task=await (await get(base+`/agent-tasks/${answer.production.taskId}`)).json();
        assert.equal(task.status,'succeeded');
        if (!apply) { assert.equal(task.result.commands.length,0,task.result.rationale);return task; }
        assert.ok(task.result.commands.length,task.result.rationale);
        doc=await (await post(base+`/agent-tasks/${task.id}/apply`,{expectedRevision:doc.revision},moduleHeaders)).json();
        return task;
    }
    await command('Faça o texto aparecer palavra por palavra',['scene-1-title']);
    await command('Deixe a primeira cena mais dinâmica');
    if (stage3) {
        await command('Troque a cor do cartão selecionado',['scene-2-card'],false);
        await command('Aumente a duração da segunda animação',[],false);
        await command('Altere somente o título da terceira cena',[],false);
        await command('Mude a duração da animação para 3 segundos',['scene-2-title']);
        await command('Altere somente o título da terceira cena para "Inove com a Clicko"');
        await command('Deixe as transições mais suaves');
        const beforeUndo=structuredClone(doc.composition);
        await command('Troque a cor do cartão selecionado para tangerina',['scene-2-card']);
        await command('Desfaça a última alteração.');
        assert.deepEqual(doc.composition,beforeUndo);
    }
    const preview=await get(base+'/local-preview?frame=36');
    writeFileSync(path.join(output,'preview-v1.png'),Buffer.from(await preview.arrayBuffer()));
    async function render(label:string) {
        let job=await (await post(`/api/v1/studios/v1/video/documents/${documentId}/render-jobs`,
            {expectedRevision:doc.revision},{...moduleHeaders,'Idempotency-Key':`${run}-${label}`})).json();
        const until=Date.now()+180_000;
        while(!['succeeded','failed','cancelled'].includes(job.status)&&Date.now()<until) {
            await new Promise(resolve=>setTimeout(resolve,500));
            job=await (await get('/api/v1/studios/v1/jobs/'+job.id)).json();
        }
        assert.equal(job.status,'succeeded',JSON.stringify(job));
        const delivery=await get(job.result.downloadUrl);
        const bytes=Buffer.from(await delivery.arrayBuffer());
        writeFileSync(path.join(output,`motion-${label}.mp4`),bytes);
        persist(`document-${label}.json`,doc);
        console.log(JSON.stringify({phase:'rendered',version:label,jobId:job.id,bytes:bytes.length}));
        return {job,bytes};
    }
    const first=await render('v1');
    const before=structuredClone(doc);
    const edit=await command('Mude a cor do título para coral',['scene-1-title']);
    for(const old of before.composition.pages[0].layers) {
        const latest=doc.composition.pages[0].layers.find((row:{id:string})=>row.id===old.id);
        if(old.id!=='scene-1-title')assert.deepEqual(latest,old);
    }
    const second=await render('v2');
    assert.equal(first.bytes.equals(second.bytes),false);
    assert.equal(first.bytes.equals(Buffer.from(await (await get(first.job.result.downloadUrl)).arrayBuffer())),true);
    const tasks=await (await get(base+'/agent-tasks')).json();
    const versions=await (await get(base+'/versions')).json();
    assert.ok(versions.length>=4);
    assert.equal(remoteProviderCalls,0);
    persist('evidence.json',{mode:'live_conversation_router_and_real_backend_deterministic_not_model_inference',
        documentId,revision:doc.revision,conversationId:conversation.id,tasks,versions:versions.length,
        paidProviderCalls:remoteProviderCalls,first:first.job,second:second.job,edit,
        isolatedProfile:profile,governanceFixture:true,authenticatedBrowserQa:false,persistenceAfterRestart:false,stage3});
    console.log(JSON.stringify({realKlicRouter:true,realBackend:true,threeScenes:true,twoRealRenders:true,
        durationSeconds:15,versions:versions.length,paidProviderCalls:remoteProviderCalls}));
} finally { await new Promise<void>(resolve=>server.close(()=>resolve())); }
