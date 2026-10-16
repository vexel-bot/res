// Capture an actual edit in an isolated test post, never a simulated UI.
import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const input=JSON.parse(raw);
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1280,height:900},
  recordVideo:{dir:path.join(input.out,'capture'),size:{width:1280,height:900}}});
await context.addInitScript(({token,workspaceId})=>{
  localStorage.setItem('nexus_access_token',token);
  localStorage.setItem('clicko:active-workspace',workspaceId);
},{token:input.token,workspaceId:input.workspaceId});
const page=await context.newPage();
const evidence=[];
try{
  await page.goto(`${input.origin??'http://127.0.0.1:3000'}/content/${input.postId}/edit?mode=video`,{waitUntil:'domcontentloaded',timeout:60000});
  const field=page.getByRole('textbox',{name:'Texto editorial das legendas'});
  await field.waitFor({timeout:60000});
  await page.waitForFunction(()=>{
    const video=document.querySelector('.vs-phone-frame video');
    return video && video.readyState>=1;
  },{},{timeout:90000});
  await page.locator('.vs-phone-frame video').evaluate(async video=>{video.muted=true;await video.play();video.pause();video.currentTime=0;});
  await page.getByRole('button',{name:'Aplicar na timeline',exact:true}).waitFor();
  await page.screenshot({path:path.join(input.out,'interface-before.png')});
  const recordingStart=Date.now();
  evidence.push({stage:'before',text:await field.inputValue()});
  if(evidence[0].text.includes('Uma ideia ganha clareza.'))throw new Error('capture_initial_state_already_final');
  await page.waitForTimeout(2200); // Initial state must remain perceptible.
  const editStartedMs=Date.now()-recordingStart;
  await field.pressSequentially('Uma ideia ganha clareza.\nEdite, aplique e confira o resultado.',{delay:25});
  evidence.push({stage:'typing',startMs:editStartedMs,endMs:Date.now()-recordingStart,
    method:'Real keyboard input, 25 ms per character'});
  await page.waitForTimeout(300);
  const saved=page.waitForResponse(response=>response.request().method()==='PUT' &&
    /\/studios\/v1\/documents\/[^/]+$/.test(new URL(response.url()).pathname),{timeout:90000});
  const applyStartedMs=Date.now()-recordingStart;
  await page.getByRole('button',{name:'Aplicar na timeline',exact:true}).click();
  const savedResponse=await saved;
  if(!savedResponse.ok())throw new Error('caption_save_failed:'+savedResponse.status());
  const document=await savedResponse.json();
  const cues=document.composition.mediaTimeline.tracks.filter(t=>t.kind==='caption').flatMap(t=>t.cues);
  if(!cues.some(c=>c.text==='Uma ideia ganha clareza.'))throw new Error('persisted_caption_missing');
  await page.locator('.vs-caption-preview').filter({hasText:'Uma ideia ganha clareza.'}).waitFor({timeout:30000});
  await page.screenshot({path:path.join(input.out,'interface-after.png')});
  const snapshot=await page.locator('body').innerText();
  if(snapshot.includes('Workspace demonstrativo')||!snapshot.includes('Uma ideia ganha clareza.'))
    throw new Error('real_persisted_interface_result_required');
  evidence.push({stage:'after',text:await field.inputValue(),applyStartedMs,resultObservedMs:Date.now()-recordingStart,
    demo:false,documentId:document.documentId,
    revision:document.revision,persistedCues:cues.map(c=>c.text)});
  await page.waitForTimeout(Math.max(1200,15000-(Date.now()-recordingStart)));
  const recordingSeconds=(Date.now()-recordingStart)/1000;
  await fs.writeFile(path.join(input.out,'interface-task-timing.json'),JSON.stringify({evidence,recordingSeconds},null,2));
  const video=page.video();
  await context.close();
  const source=await video.path(),destination=path.join(input.out,'interface-task.mp4');
  const probe=spawnSync('ffprobe',['-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',source],{encoding:'utf8',windowsHide:true});
  if(probe.status!==0)throw new Error(probe.stderr);
  const start=Math.max(0,Number(probe.stdout)-recordingSeconds);
  let intervals=[[0,Math.min(15,recordingSeconds)]];
  if(recordingSeconds>16){
    const cutAt=applyStartedMs/1000+.5;
    const resumeAt=(evidence.find(e=>e.stage==='after').resultObservedMs/1000)-1;
    if(cutAt>=11||resumeAt<=cutAt||recordingSeconds-resumeAt<1)throw new Error('capture_wait_cannot_be_cut_safely');
    intervals=[[0,cutAt],[resumeAt,recordingSeconds]];
  }
  const segments=intervals.map(([from,to],index)=>`[0:v]trim=start=${start+from}:end=${start+to},setpts=PTS-STARTPTS[v${index}]`);
  const filter=segments.join(';')+';'+intervals.map((_,i)=>`[v${i}]`).join('')+
    `concat=n=${intervals.length}:v=1:a=0,tpad=stop_mode=clone:stop_duration=15,fps=30[out]`;
  const result=spawnSync('ffmpeg',['-v','error','-y','-i',source,'-filter_complex',filter,'-map','[out]',
    '-t','15','-an','-c:v','libx264','-pix_fmt','yuv420p',destination],{encoding:'utf8',windowsHide:true});
  if(result.status!==0)throw new Error(result.stderr);
  await fs.writeFile(path.join(input.out,'interface-capture-evidence.json'),JSON.stringify({evidence,source,output:destination,
    trimStartSeconds:start,recordingSeconds,sourceIntervals:intervals,
    editorialIntervention:intervals.length===2?'Cut only idle save wait; retain actual typing, apply and result at normal speed; hold final frame':'Trim startup and hold final frame',
    timingObservation:'UI wall clock, not encoded event-frame measurement'},null,2));
  console.log(JSON.stringify({path:destination,evidence,realApplication:true,manualIntervention:'UI task directed by automation for recording'}));
}catch(error){
  await fs.writeFile(path.join(input.out,'interface-capture-failure.log'),String(error.stack??error));
  if(!page.isClosed()){
    await page.screenshot({path:path.join(input.out,'interface-failure.png')}).catch(()=>{});
    await fs.writeFile(path.join(input.out,'interface-failure.txt'),await page.locator('body').innerText().catch(()=>''));
  }
  throw error;
}finally{await browser.close();}
