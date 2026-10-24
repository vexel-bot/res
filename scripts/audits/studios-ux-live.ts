/** Real DEV API smoke for the frontend's existing create/import/save/export contracts. Not browser QA. */
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { DEV_USER_ID, DEV_WORKSPACE_ID, DEV_CLIENT_ID } from '../../src/development/contracts';
const root = path.resolve(import.meta.dirname,'../..'); process.chdir(root);
const output = path.join(root,'.codex-runtime/studios-ux'); mkdirSync(output,{recursive:true});
const status = JSON.parse(execFileSync(process.execPath,['scripts/dev-local.mjs','status'],{encoding:'utf8'}));
assert.equal(status.ready,true); assert.equal(path.resolve(status.dataDirectory),path.join(root,'.codex-runtime/clicko-dev'));
const origin='http://127.0.0.1:3018',base='/api/v1/studios/v1';
const auth=await fetch(origin+'/api/governance/auth/session'); assert.equal((await auth.json()).user.id,DEV_USER_ID);
const cookie=auth.headers.get('set-cookie')?.split(';')[0]; assert.ok(cookie);
const headers: Record<string,string>={cookie,'x-workspace-id':DEV_WORKSPACE_ID,'x-clicko-client-id':DEV_CLIENT_ID,'x-clicko-studio-module':'create-image'};
async function json(route:string, body?:unknown) {
  const response=await fetch(origin+route,{method:body===undefined?'GET':'POST',signal:AbortSignal.timeout(120000),
    headers:{...headers,...(body instanceof FormData?{}:{'Content-Type':'application/json'}),...(body===undefined?{}:{'Idempotency-Key':randomUUID()})},
    body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)});
  if(!response.ok)throw new Error(`${route}: ${response.status} ${await response.text()}`); return response.json();
}
const health=await json('/api/development/status'); assert.equal(health.costs.externalCallsEnabled,false);
const workspace=(await json(base+'/bridge/session')).workspace.id;
const run=randomUUID(), hash=(bytes:Uint8Array)=>createHash('sha256').update(bytes).digest('hex');
const original=readFileSync(path.join(root,'.codex-runtime/audit-2026-10-23/source-card.png'));
const form=new FormData();form.set('workspace_id',workspace);form.set('title','UX · Material próprio');form.set('file',new Blob([original],{type:'image/png'}),'ux-source.png');
const asset=await json('/api/v1/assets/upload',form); assert.equal(asset.checksumSha256,hash(original));
let image=await json(base+'/agents/projects',{workspaceId:workspace,title:'UX · Imagem vertical · '+run,contentType:'visual',width:720,height:1280});
const layer={id:'graphic',kind:'image',name:'Material importado',x:60,y:80,width:600,height:300,rotation:0,opacity:1,visible:true,locked:false,zIndex:0,
  properties:{schemaVersion:'studio.local-layer.v1',assetId:asset.id,crop:{x:.1,y:.1,width:.8,height:.8},brightness:1.1,contrast:1.05,saturation:.9}};
image=await json(`${base}/documents/${image.documentId}/local-commands`,{expectedRevision:image.revision,commands:[{id:'asset.attach',params:{assetId:asset.id}},{id:'layer.upsert',params:{layer}}]});
const png=await json(`${base}/documents/${image.documentId}/local-image-export`,{expectedRevision:image.revision});
async function download(url:string,file:string) { const response=await fetch(origin+url,{headers,signal:AbortSignal.timeout(120000)});assert.ok(response.ok);const bytes=new Uint8Array(await response.arrayBuffer());writeFileSync(path.join(output,file),bytes);return{file,sha256:hash(bytes),bytes:bytes.length}; }
const imageDelivery=await download(png.downloadUrl,'image.png');
headers['x-clicko-studio-module']='create-video';
let video=await json(base+'/agents/projects',{workspaceId:workspace,title:'UX · Montagem · '+run,contentType:'video',width:640,height:360});
const composition=structuredClone(video.composition);composition.pages[0].durationMs=2000;composition.mediaTimeline.durationFrames=48;
composition.pages[0].layers=[{...layer,id:'title',kind:'text',name:'Título editável',x:40,y:110,width:560,height:120,properties:{schemaVersion:'studio.local-layer.v1',text:'Clicko · Novo workspace',fontSize:38,fontFamily:'system',color:'#FF7F50',durationFrames:48,keyframes:[{property:'opacity',frame:0,value:0},{property:'opacity',frame:12,value:1,easing:'ease-out'}]}}];
video=await json(`${base}/documents/${video.documentId}/local-commands`,{expectedRevision:video.revision,commands:[{id:'composition.replace',params:{composition}}]});
let job=await json(`${base}/video/documents/${video.documentId}/render-jobs`,{expectedRevision:video.revision});
const deadline=Date.now()+120000;
while(!['succeeded','failed','cancelled'].includes(job.status)&&Date.now()<deadline){await new Promise(resolve=>setTimeout(resolve,500));job=await json(`${base}/jobs/${job.id}`);}
assert.equal(job.status,'succeeded');const videoDelivery=await download(job.result.downloadUrl,'video.mp4');
const saved=await json(`${base}/documents/${video.documentId}`);assert.equal(saved.revision,video.revision);
const versions=await json(`${base}/documents/${video.documentId}/versions`);assert.ok(versions.length>=1);
const source=await fetch(origin+`/api/v1/assets/${asset.id}/content`,{headers});assert.equal(hash(new Uint8Array(await source.arrayBuffer())),hash(original));
writeFileSync(path.join(output,'evidence.json'),JSON.stringify({run,imageDocument:image.documentId,videoDocument:video.documentId,revision:video.revision,versions:versions.length,imageDelivery,videoDelivery,originalPreserved:true,externalCostUsd:0,browserQa:false},null,2));
console.log(JSON.stringify({realDevSession:true,import:true,save:true,png:true,mp4:true,versions:true,originalPreserved:true,browserQa:false,externalCostUsd:0}));
