param([Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9-]+$')][string]$Stage)
$ErrorActionPreference = 'Stop'
$taskOut = Join-Path (Get-Location) 'docs/studios/research/editor-oss-20261002/temporal-matte-composition-preview'
$taskTarget = Join-Path $taskOut "ui-$Stage.json"
if (Test-Path -LiteralPath $taskTarget) { throw 'Preserve existing browser capture' }
$taskScript = @'
(() => {
  const section=document.querySelector('.editor-inspection');
  const stage=document.querySelector('.vs-stage');
  if(!stage) throw new Error('Real video studio stage required');
  const video=stage.querySelector('video');
  const box=stage.querySelector('.vs-phone-frame');
  const r=box.getBoundingClientRect();
  let pixels=null;
  if(video && video.readyState>=2 && !video.seeking){
    const c=document.createElement('canvas');c.width=video.videoWidth;c.height=video.videoHeight;
    const context=c.getContext('2d');context.drawImage(video,0,0);
    pixels=[[50,60],[64,60],[150,150]].map(([x,y])=>({x,y,rgb:[...context.getImageData(x,y,1,1).data].slice(0,3)}));
  }
  return {scope:'actual_browser_UI_no_mock',observedAt:new Date().toISOString(),url:location.href,
    stageText:stage.innerText,toolbar:stage.querySelector('.vs-stage-toolbar').innerText,
    frameRect:{x:r.x,y:r.y,width:r.width,height:r.height},
    frameClass:box.className,overlayCount:box.querySelectorAll('.vs-safe-area,.vs-caption-preview,.vs-brand-overlay,.vs-brand-text-overlay').length,
    computedAspect:getComputedStyle(box).aspectRatio,
    video:video?{src:video.currentSrc,readyState:video.readyState,seeking:video.seeking,currentTime:video.currentTime,
      duration:video.duration,paused:video.paused,muted:video.muted,width:video.videoWidth,height:video.videoHeight,objectFit:getComputedStyle(video).objectFit}:null,
    pixels,compositionFrame:section?.querySelector('input[aria-label="Frame da composição"]')?.value??null,
    selectedLayer:section?.querySelector('select[aria-label="Camada"]')?.value??null,
    inspectorText:section?.offsetParent?section.innerText:null,
    inspectorVideo:section?.querySelector('video')?{src:section.querySelector('video').currentSrc,currentTime:section.querySelector('video').currentTime,paused:section.querySelector('video').paused}:null,
    activeAudioSources:document.querySelectorAll('audio').length};
})()
'@
$taskEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskScript))
$taskRaw=agent-browser --session res-matte-inspection-20261004 --json eval -b $taskEncoded
if($LASTEXITCODE -ne 0){throw 'Browser capture failed'}
$taskData=$taskRaw | ConvertFrom-Json
if(-not $taskData.success){throw $taskData.error}
[IO.File]::WriteAllText($taskTarget, ($taskRaw -join "`n"), [Text.UTF8Encoding]::new($false))
@{stage=$Stage;videoPresent=[bool]$taskData.data.result.video;frame=$taskData.data.result.compositionFrame;aspect=$taskData.data.result.computedAspect} | ConvertTo-Json -Compress
