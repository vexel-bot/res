// Development verification in an isolated context. No human review is submitted.
import {chromium} from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';
let raw='';for await(const chunk of process.stdin)raw+=chunk;
const input=JSON.parse(raw);
const browser=await chromium.launch({headless:true});
const context=await browser.newContext({viewport:{width:1280,height:900}});
await context.addInitScript(({token,workspaceId})=>{
  localStorage.setItem('nexus_access_token',token);
  localStorage.setItem('clicko:active-workspace',workspaceId);
},{token:input.token,workspaceId:input.workspaceId});
const page=await context.newPage();
// The isolated development server has watching disabled. Fetch the current
// component from that same server under a fresh module URL, never mock its body.
await page.route('**/VisualStudyComparisonPanel.tsx*',route=>{
  const url=new URL(route.request().url());
  url.searchParams.set('study-ui-revision','modal-v1');
  return route.continue({url:url.toString()});
});
const evidence=[];
try{
  for(const study of input.studies){
    await page.goto(study.url,{waitUntil:'domcontentloaded',timeout:60000});
    await page.getByRole('button',{name:'Revisão',exact:true}).click();
    const panel=page.locator('[aria-label="Comparação cega dos estudos próprios"]');
    await panel.waitFor({timeout:90000});
    await panel.getByRole('button',{name:'Abrir três opções'}).click();
    await panel.getByRole('dialog',{name:'Revisão cega em tamanho de celular'}).waitFor({timeout:30000});
    const videos=panel.locator('video');
    await videos.nth(2).waitFor({timeout:30000});
    const scores=await panel.locator('input[type="number"]').evaluateAll(inputs=>inputs.map(x=>x.value));
    if(scores.length!==5 || scores.some(Boolean))throw new Error('human_scores_must_be_blank');
    if(await panel.getByRole('button',{name:'Registrar avaliação humana'}).isEnabled())
      throw new Error('incomplete_human_review_must_be_disabled');
    const playbacks=[];
    for(let i=0;i<3;i++){
      const video=videos.nth(i);
      await video.scrollIntoViewIfNeeded();
      const visibility=await video.evaluate(v=>{
        const r=v.getBoundingClientRect();
        return {top:r.top,bottom:r.bottom,width:r.width,height:r.height,viewportHeight:innerHeight};
      });
      if(visibility.top<0||visibility.bottom>visibility.viewportHeight||visibility.width<250)
        throw new Error('phone_preview_not_visible_in_viewport');
      const started=Date.now();
      await video.evaluate(async v=>{v.muted=true;v.currentTime=0;v.playbackRate=1;await v.play();});
      await page.waitForFunction(index=>{
        const v=document.querySelectorAll('[aria-label="Comparação cega dos estudos próprios"] video')[index];
        return v && v.ended && v.currentTime>=14.9;
      },i,{timeout:25000});
      playbacks.push(await video.evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,
        displayWidth:v.getBoundingClientRect().width,ended:v.ended,playbackRate:v.playbackRate,audioVerified:false})));
      playbacks.at(-1).wallMs=Date.now()-started;
      await page.screenshot({path:path.join(input.out,`studio-${study.name}-option-${i+1}.png`)});
      console.log(JSON.stringify({study:study.name,option:i+1,playback:'ended',humanEvaluation:'pending'}));
    }
    await panel.locator('input[type="number"]').first().scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(input.out,`studio-${study.name}-comparison.png`)});
    evidence.push({study:study.name,url:study.url,blankHumanScores:true,reviewNotSubmitted:true,playbacks});
  }
  await fs.writeFile(path.join(input.out,'studio-verification.json'),JSON.stringify({
    evidence,scope:'Mechanical playback verification, not human aesthetic or acoustic evaluation',
    humanReview:'pending',autonomy:'not_demonstrated'},null,2));
}catch(error){
  await page.screenshot({path:path.join(input.out,'studio-verification-failure.png')});
  throw error;
}finally{await browser.close();}
