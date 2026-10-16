param(
  [Parameter(Mandatory=$true)][ValidateSet('arm','collect')][string]$Phase,
  [ValidatePattern('^[a-z0-9-]+$')][string]$Observation = 'first',
  [ValidatePattern('^[a-z0-9-]+$')][string]$BrowserSession = 'res-layer-timeline-20261005'
)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut = Join-Path $taskRoot 'docs/studios/research/editor-oss-20261002/output-render-routing'
$taskTarget = Join-Path $taskOut "high-ui-playback-$Observation-$Phase.json"
if (Test-Path -LiteralPath $taskTarget) { throw 'Preserve existing browser observation' }
$taskScript = if ($Phase -eq 'arm') { @'
(async () => {
  window.__resOutputPlaybackObservations??={};
  if(window.__resOutputPlaybackObservations['OBSERVATION_KEY']) throw new Error('Existing observer must be preserved');
  const video=document.querySelector('.vs-stage video');
  const download=document.querySelector('.vs-render-artifact a[download]');
  if(!video || !download || video.readyState<2 || !video.paused || video.currentTime>0.001)
    throw new Error('Ready current output at frame zero required');
  const bytes=await fetch(video.currentSrc).then(r=>{if(!r.ok)throw new Error('Displayed MP4 unavailable');return r.arrayBuffer()});
  const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
  const data={scope:'Passive observation of actual UI playback; no simulated video or altered playback rate',
    observedAt:new Date().toISOString(),url:location.href,sha256,bytes:bytes.byteLength,
    width:video.videoWidth,height:video.videoHeight,duration:video.duration,initialTime:video.currentTime,
    initialRate:video.playbackRate,muted:video.muted,downloadName:download.download,
    downloadMatchesPlayer:download.href===video.currentSrc,
    overlayCount:document.querySelector('.vs-phone-frame').querySelectorAll('.vs-safe-area,.vs-caption-preview,.vs-brand-overlay,.vs-brand-text-overlay').length,
    stageText:document.querySelector('.vs-stage').innerText,events:[],samples:[]};
  const observer={data,video,timer:null,started:null,ended:null};
  const sample=()=>data.samples.push({elapsedMs:observer.started===null?null:performance.now()-observer.started,
    time:video.currentTime,paused:video.paused,ended:video.ended,rate:video.playbackRate,
    readyState:video.readyState,seeking:video.seeking,
    otherPlayingVideos:[...document.querySelectorAll('video')].filter(v=>v!==video&&!v.paused&&!v.ended).length});
  for(const name of ['play','playing','pause','waiting','seeking','seeked','ended','error'])
    video.addEventListener(name,()=>{
      if(name==='play'&&observer.started===null) observer.started=performance.now();
      if(name==='ended') observer.ended=performance.now();
      data.events.push({name,time:video.currentTime,elapsedMs:observer.started===null?null:performance.now()-observer.started});
      sample();
    });
  sample();observer.timer=setInterval(sample,250);window.__resOutputPlaybackObservations['OBSERVATION_KEY']=observer;
  return {...data,events:[],samples:data.samples.slice()};
})()
'@ } else { @'
(async () => {
  const observer=window.__resOutputPlaybackObservations?.['OBSERVATION_KEY'];
  if(!observer) throw new Error('Arm the passive observer before clicking the real playback button');
  const deadline=performance.now()+23000;
  while(observer.ended===null&&performance.now()<deadline) await new Promise(resolve=>setTimeout(resolve,100));
  clearInterval(observer.timer);
  return {...observer.data,completedAt:new Date().toISOString(),reachedEnd:observer.video.ended,
    finalTime:observer.video.currentTime,playbackWallMs:observer.ended===null?null:observer.ended-observer.started,
    finalRate:observer.video.playbackRate,error:observer.video.error?.code??null};
})()
'@ }
$taskScript = $taskScript.Replace('OBSERVATION_KEY', $Observation)
$taskEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskScript))
$taskRaw = agent-browser --session $BrowserSession --json eval -b $taskEncoded
if ($LASTEXITCODE -ne 0) { throw 'Browser observation failed' }
$taskData = $taskRaw | ConvertFrom-Json
if (-not $taskData.success) { throw $taskData.error }
$taskObserved = $taskData.data.result
$taskJob = Get-Content -LiteralPath (Join-Path $taskOut 'high-job-terminal.json') -Raw | ConvertFrom-Json
if ($taskJob.status -ne 'succeeded' -or $taskObserved.sha256 -ne $taskJob.result.artifact.checksumSha256 -or
    $taskObserved.bytes -ne $taskJob.result.artifact.sizeBytes) { throw 'Observed MP4 differs from real render job' }
[IO.File]::WriteAllText($taskTarget, ($taskRaw -join "`n"), [Text.UTF8Encoding]::new($false))
if ($Phase -eq 'collect' -and (-not $taskObserved.reachedEnd -or $taskObserved.finalTime -ne 15 -or
    $taskObserved.finalRate -ne 1 -or $taskObserved.error -or $taskObserved.playbackWallMs -lt 14500 -or
    ($taskObserved.samples | Where-Object { $_.otherPlayingVideos -ne 0 -or $_.seeking -or $_.rate -ne 1 }))) {
  throw 'Retained observation does not qualify uninterrupted exclusive normal-speed playback'
}
$taskObserved | Select-Object sha256,bytes,width,height,duration,reachedEnd,finalTime,playbackWallMs | ConvertTo-Json -Compress
