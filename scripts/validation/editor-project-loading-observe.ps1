param(
  [Parameter(Mandatory=$true)][ValidateSet('arm','collect')][string]$Phase,
  [Parameter(Mandatory=$true)][ValidateSet('fault','recovered')][string]$Stage,
  [ValidatePattern('^[a-z0-9-]+$')][string]$Observation = 'verified',
  [ValidatePattern('^[a-z0-9-]+$')][string]$BrowserSession = 'res-output-download-20261005'
)
$ErrorActionPreference='Stop'
$taskRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut=Join-Path $taskRoot 'docs/studios/research/editor-oss-20261002/project-loading'
$taskTarget=Join-Path $taskOut "$Stage-$Observation-$Phase.json"
if(Test-Path -LiteralPath $taskTarget){throw 'Preserve existing loading observation'}
$taskScript=if($Phase -eq 'arm'){@'
(()=>{
 window.__resProjectLoadObservations??={};
 if(window.__resProjectLoadObservations['OBSERVER_KEY'])throw new Error('Preserve existing observer');
 const observer={start:performance.now(),observedAt:new Date().toISOString(),samples:[],timer:null};
 observer.sample=()=>{
  const video=document.querySelector('.vs-stage video');
  observer.samples.push({elapsedMs:performance.now()-observer.start,
   health:document.querySelector('.vs-health')?.innerText??null,
   supportLoading:[...document.querySelectorAll('[role="status"]')].some(e=>e.innerText.includes('Carregando repertório e auditorias de apoio')),
   warnings:[...document.querySelectorAll('.vs-error-box')].map(e=>e.innerText),
   videoReady:!!video&&video.readyState>=2,videoTime:video?.currentTime??null,
   previewEnabled:!document.querySelector('.vs-stage [data-action-id="VIDEO-TOGGLE-PLAYBACK"]')?.disabled,
   layerRows:document.querySelectorAll('.vs-canonical-lane button').length});
 };
 observer.sample();observer.timer=setInterval(observer.sample,100);
 window.__resProjectLoadObservations['OBSERVER_KEY']=observer;
 return {scope:'Passive visible DOM observation before actual refresh control',observedAt:observer.observedAt,url:location.href,before:observer.samples[0]};
})()
'@}else{@'
(async()=>{
 const o=window.__resProjectLoadObservations?.['OBSERVER_KEY'];if(!o)throw new Error('Arm before refresh');
 const fault='STAGE_KEY'==='fault',deadline=performance.now()+30000;
 const complete=()=>{
  const s=o.samples.at(-1),loadingWasObserved=o.samples.some(x=>x.health==='Carregando projeto');
  const warningText=s?.warnings.join(' ')??'';
  return loadingWasObserved&&s?.health==='MP4 pronto para revisão'&&s.videoReady&&!s.supportLoading&&
   (fault?warningText.includes('Auditoria de capacidades')&&warningText.includes('Auditoria de autonomia'):!warningText);
 };
 while(!complete()&&performance.now()<deadline)await new Promise(resolve=>setTimeout(resolve,100));
 clearInterval(o.timer);o.sample();
 const video=document.querySelector('.vs-stage video');
 if(!video||video.readyState<2)throw new Error('Actual canonical video must be loaded');
 const bytes=await fetch(video.currentSrc).then(r=>{if(!r.ok)throw new Error('Displayed MP4 unavailable');return r.arrayBuffer()});
 const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const resources=performance.getEntriesByType('resource').filter(x=>x.startTime>=o.start&&new URL(x.name).pathname.startsWith('/api/'))
  .map(x=>({path:new URL(x.name).pathname,startMs:x.startTime-o.start,endMs:x.responseEnd-o.start,durationMs:x.duration,responseStatus:x.responseStatus??null}));
 return {scope:'Real current document and MP4; two optional requests aborted locally only in fault stage',
  stage:'STAGE_KEY',observedAt:o.observedAt,completedAt:new Date().toISOString(),url:location.href,
  completed:complete(),samples:o.samples,resources,video:{sha256,bytes:bytes.byteLength,duration:video.duration,width:video.videoWidth,height:video.videoHeight},
  warningTexts:o.samples.at(-1).warnings,overlayErrors:document.querySelectorAll('vite-error-overlay').length};
})()
'@}
$taskScript=$taskScript.Replace('STAGE_KEY',$Stage).Replace('OBSERVER_KEY',"$Stage-$Observation")
$taskEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskScript))
$taskRaw=agent-browser --session $BrowserSession --json eval -b $taskEncoded
if($LASTEXITCODE -ne 0){throw 'Browser observation failed'}
$taskData=$taskRaw|ConvertFrom-Json
if(-not $taskData.success){throw $taskData.error}
[IO.File]::WriteAllText($taskTarget,($taskRaw -join "`n"),[Text.UTF8Encoding]::new($false))
$taskObserved=$taskData.data.result
if($Phase -eq 'collect'){
 $taskPrior=Get-Content -LiteralPath (Join-Path $taskRoot 'docs/studios/research/editor-oss-20261002/output-render-routing/high-job-terminal.json') -Raw|ConvertFrom-Json
 if(-not $taskObserved.completed -or $taskObserved.video.sha256 -ne $taskPrior.result.artifact.checksumSha256 -or $taskObserved.overlayErrors){throw 'Retained observation did not qualify current project recovery'}
 $taskObserved|Select-Object stage,completed,video,warningTexts|ConvertTo-Json -Compress -Depth 5
}else{$taskObserved|Select-Object observedAt,before|ConvertTo-Json -Compress -Depth 5}
