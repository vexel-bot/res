#requires -Version 7.0
param(
  [Parameter(Mandatory=$true)][ValidateSet('organization-a','comparison-a')][string]$Study,
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9-]+$')][string]$Stage,
  [Parameter(Mandatory=$true)][ValidateRange(0,449)][int]$Frame,
  [switch]$Inspection,
  [switch]$HashVideo
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$taskOut = Join-Path (Get-Location) 'docs/studios/research/editor-oss-20261002/canonical-layer-timeline/live-other-studies'
$taskTarget = Join-Path $taskOut "$Study-$Stage.json"
if (Test-Path -LiteralPath $taskTarget) { throw 'Preserve existing observation' }
$taskJs = @'
(async () => {
  const expected = __FRAME__;
  const inspectionRequired = __INSPECTION__;
  const deadline = performance.now() + 20000;
  let ready = false;
  while (performance.now() < deadline) {
    const v = document.querySelector('.vs-stage video');
    const ruler = document.querySelector('[aria-label="Playhead da composição"]');
    const section = document.querySelector('.editor-inspection');
    const inspectorReady = !inspectionRequired || (section?.offsetParent && section.innerText.includes(`Propriedades calculadas no frame ${expected}.`));
    if (v?.readyState >= 2 && !v.seeking && Math.abs(v.currentTime - expected / 30) < 1/60
        && Number(ruler?.getAttribute('aria-valuenow')) === expected && inspectorReady) { ready = true; break; }
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  const stage = document.querySelector('.vs-stage');
  const video = stage?.querySelector('video');
  const ruler = document.querySelector('[aria-label="Playhead da composição"]');
  const inspector = document.querySelector('.editor-inspection');
  let sha256 = null, bytes = null;
  if (__HASH__ && video?.currentSrc.startsWith('blob:')) {
    const response = await fetch(video.currentSrc);
    const data = await response.arrayBuffer(); bytes = data.byteLength;
    sha256 = [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(x => x.toString(16).padStart(2,'0')).join('');
  }
  return {observedAt: new Date().toISOString(), scope:'Public DOM, existing authenticated document and MP4; no editor mutations',
    ready, url: location.href, expectedFrame: expected,
    ruler: ruler ? {min:ruler.getAttribute('aria-valuemin'),max:ruler.getAttribute('aria-valuemax'),frame:ruler.getAttribute('aria-valuenow')} : null,
    rows:[...document.querySelectorAll('.vs-canonical-row button')].map(b=>({layerId:b.dataset.layerId,sceneId:b.dataset.sceneId,startFrame:Number(b.dataset.startFrame),durationFrames:Number(b.dataset.durationFrames),label:b.getAttribute('aria-label')})),
    video:video?{currentTime:video.currentTime,readyState:video.readyState,seeking:video.seeking,paused:video.paused,width:video.videoWidth,height:video.videoHeight,duration:video.duration,sha256,bytes}:null,
    stageText:stage?.innerText,
    inspector:inspector?.offsetParent?{text:inspector.innerText,frame:inspector.querySelector('[aria-label="Frame da composição"]')?.value,layerId:inspector.querySelector('[aria-label="Camada"]')?.value,sceneId:inspector.querySelector('[aria-label="Cena"]')?.value}:null,
    overlays:document.querySelectorAll('vite-error-overlay').length,
    resources:performance.getEntriesByType('resource').filter(x=>new URL(x.name).pathname.startsWith('/api/')).map(x=>({path:new URL(x.name).pathname,status:x.responseStatus,durationMs:x.duration}))};
})()
'@
$taskJs = $taskJs.Replace('__FRAME__', [string]$Frame).Replace('__INSPECTION__', $Inspection.IsPresent.ToString().ToLowerInvariant()).Replace('__HASH__', $HashVideo.IsPresent.ToString().ToLowerInvariant())
$taskEncoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskJs))
$taskRaw = agent-browser --session res-output-download-20261005 --json eval -b $taskEncoded
if ($LASTEXITCODE -ne 0) { throw 'Browser observation failed' }
$taskData = $taskRaw | ConvertFrom-Json
if (-not $taskData.success) { throw $taskData.error }
[IO.File]::WriteAllText($taskTarget, ($taskRaw -join "`n"), [Text.UTF8Encoding]::new($false))
@{study=$Study;stage=$Stage;ready=$taskData.data.result.ready;frame=$taskData.data.result.ruler.frame;rows=$taskData.data.result.rows.Count;selected=$taskData.data.result.inspector.layerId;sha256=$taskData.data.result.video.sha256} | ConvertTo-Json -Compress
if (-not $taskData.data.result.ready) { throw 'Expected UI and decoded frame not observed; observation retained' }
