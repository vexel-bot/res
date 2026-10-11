param(
  [Parameter(Mandatory=$true)][ValidateSet('organization-a','comparison-a','interface-a')][string]$Key,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9-]+$')][string]$Stage,
  [ValidatePattern('^[a-z0-9-]+$')][string]$BrowserSession = 'res-directed-native14-editor-20261004'
)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskOut = Join-Path $taskRoot 'docs/studios/research/editor-oss-20261002/directed-native14-portrait-ui'
[IO.Directory]::CreateDirectory($taskOut) | Out-Null
$taskTarget = Join-Path $taskOut "$Key-$Stage.json"
if (Test-Path -LiteralPath $taskTarget) { throw 'Preserve retained browser observation' }
$taskState = Get-Content -LiteralPath (Join-Path $taskRoot 'output/visual-directed-native14-20261004/execution.json') -Raw | ConvertFrom-Json
$taskVariant = $taskState.variants.$Key
if (-not $taskVariant.artifact) { throw 'Collected canonical render required' }
$taskScript = @'
(async () => {
  const stage=document.querySelector('.vs-stage');
  const inspector=document.querySelector('.editor-inspection');
  const video=stage?.querySelector('video');
  const frame=stage?.querySelector('.vs-phone-frame');
  if(!stage||!frame||!video||video.readyState<2||video.seeking) throw new Error('Loaded real Studio MP4 required');
  const rect=frame.getBoundingClientRect();
  const wrap=stage.querySelector('.vs-canvas-wrap').getBoundingClientRect();
  const view=stage.getBoundingClientRect();
  const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  const context=canvas.getContext('2d');context.drawImage(video,0,0);
  const points=[[120,810],[328,420],[400,1080],[650,1370],[280,1540],[500,300],[20,20]];
  const pixels=points.map(([x,y])=>({x,y,rgb:[...context.getImageData(x,y,1,1).data].slice(0,3)}));
  const blob=await fetch(video.currentSrc).then(r=>{if(!r.ok)throw new Error('Displayed blob unavailable');return r.arrayBuffer()});
  const digest=await crypto.subtle.digest('SHA-256',blob);
  const sha256=[...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,'0')).join('');
  const inspectedVideo=inspector?.querySelector('video');
  return {scope:'real_VideoStudio_current_canonical_MP4_no_mock',observedAt:new Date().toISOString(),url:location.href,
    toolbar:stage.querySelector('.vs-stage-toolbar')?.innerText,stageText:stage.innerText,
    frameClass:frame.className,computedAspect:getComputedStyle(frame).aspectRatio,
    frameRect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},
    wrapRect:{x:wrap.x,y:wrap.y,width:wrap.width,height:wrap.height},
    stageRect:{x:view.x,y:view.y,width:view.width,height:view.height},
    viewport:{width:innerWidth,height:innerHeight},
    overlayCount:frame.querySelectorAll('.vs-safe-area,.vs-caption-preview,.vs-brand-overlay,.vs-brand-text-overlay').length,
    video:{src:video.currentSrc,sha256,bytes:blob.byteLength,currentTime:video.currentTime,duration:video.duration,
      width:video.videoWidth,height:video.videoHeight,readyState:video.readyState,seeking:video.seeking,
      paused:video.paused,muted:video.muted,objectFit:getComputedStyle(video).objectFit},pixels,
    seek:stage.querySelector('input[aria-label="Posição do vídeo"]')?{
      value:stage.querySelector('input[aria-label="Posição do vídeo"]').value,
      maximum:stage.querySelector('input[aria-label="Posição do vídeo"]').max,
      step:stage.querySelector('input[aria-label="Posição do vídeo"]').step}:null,
    compositionFrame:inspector?.querySelector('input[aria-label="Frame da composição"]')?.value??null,
    inspectorText:inspector?.offsetParent?inspector.innerText:null,
    selectedLayer:inspector?.querySelector('select[aria-label="Camada"]')?.value??null,
    inspectorVideo:inspectedVideo?{src:inspectedVideo.currentSrc,currentTime:inspectedVideo.currentTime,
      readyState:inspectedVideo.readyState,seeking:inspectedVideo.seeking,paused:inspectedVideo.paused}:null,
    domAudioElements:document.querySelectorAll('audio').length,
    canonicalTimeline:document.querySelector('.vs-canonical-timeline')?{
      text:document.querySelector('.vs-canonical-timeline').innerText,
      maximum:document.querySelector('.vs-canonical-ruler').getAttribute('aria-valuemax'),
      frame:document.querySelector('.vs-canonical-ruler').getAttribute('aria-valuenow'),
      rows:[...document.querySelectorAll('.vs-canonical-lane button')].map(b=>({
        layerId:b.dataset.layerId,sceneId:b.dataset.sceneId,startFrame:b.dataset.startFrame,
        durationFrames:b.dataset.durationFrames,sourceStartSeconds:b.dataset.sourceStartSeconds,
        playbackRate:b.dataset.playbackRate,label:b.getAttribute('aria-label'),left:b.style.left,width:b.style.width})),
      legacyClips:document.querySelectorAll('.vs-video-clip').length,
      trimControls:document.querySelectorAll('.vs-trim-handle').length}:null};
})()
'@
$taskEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskScript))
$taskRaw = agent-browser --session $BrowserSession --json eval -b $taskEncoded
if ($LASTEXITCODE -ne 0) { throw 'Actual browser observation failed' }
$taskData = $taskRaw | ConvertFrom-Json
if (-not $taskData.success) { throw $taskData.error }
$taskObserved = $taskData.data.result
if ($Stage -match '^(?:timeline-)?frame(\d+)$') {
  $taskFrame = [int]$Matches[1]
  if ($taskObserved.compositionFrame -ne [string]$taskFrame -or
      $taskObserved.inspectorText -notmatch "Propriedades calculadas no frame $taskFrame\." -or
      [Math]::Abs($taskObserved.video.currentTime - $taskFrame / 30.0) -gt 0.000002 -or
      [Math]::Abs($taskObserved.inspectorVideo.currentTime - $taskFrame / 30.0) -gt 0.000002 -or
      $taskObserved.inspectorVideo.seeking) { throw 'Frame inspection/players have not settled; capture not certified' }
}
if ($taskObserved.url -ne $taskVariant.url -or $taskObserved.video.sha256 -ne $taskVariant.artifact.checksumSha256) {
  throw 'Displayed project/MP4 mismatch; do not certify the capture'
}
[IO.File]::WriteAllText($taskTarget, ($taskRaw -join "`n"), [Text.UTF8Encoding]::new($false))
@{key=$Key;stage=$Stage;frame=$taskObserved.compositionFrame;time=$taskObserved.video.currentTime;
  width=$taskObserved.video.width;height=$taskObserved.video.height;sha256=$taskObserved.video.sha256} | ConvertTo-Json -Compress
