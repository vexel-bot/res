$ErrorActionPreference='Stop'
$taskTarget=Join-Path (Get-Location) 'docs/studios/research/editor-oss-20261002/temporal-matte-composition-preview/ui-playback-observation.json'
if(Test-Path -LiteralPath $taskTarget){throw 'Preserve existing playback observation'}
$taskScript=@'
(async () => {
  const stage=document.querySelector('.vs-stage');
  const center=stage?.querySelector('video');
  const inspected=document.querySelector('.editor-inspection video');
  const button=stage?.querySelector('.vs-player-controls button');
  if(!center || !inspected || !button || center.readyState<2 || center.currentTime>0.01)
    throw new Error('Loaded real revision video at frame zero required');
  const pause=()=>new Promise(resolve=>setTimeout(resolve,40));
  const state=()=>({centerPaused:center.paused,inspectorPaused:inspected.paused,
    centerTime:center.currentTime,inspectorTime:inspected.currentTime,centerSrc:center.currentSrc,inspectorSrc:inspected.currentSrc});
  const before=state();
  button.click();await pause();const afterCenterButton=state();
  await inspected.play();await pause();const afterInspectorPlayEvent=state();
  button.click();await pause();const afterCenterResumeButton=state();
  center.pause();inspected.pause();
  return {scope:'actual_UI_center_button_and_native_inspector_play_event',observedAt:new Date().toISOString(),
    url:location.href,before,afterCenterButton,afterInspectorPlayEvent,afterCenterResumeButton,
    limitation:'Synthetic silent fixture; this measures player arbitration, not audible audio quality.'};
})()
'@
$taskEncoded=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskScript))
$taskRaw=agent-browser --session res-matte-inspection-20261004 --json eval -b $taskEncoded
if($LASTEXITCODE -ne 0){throw 'Playback observation failed'}
$taskData=$taskRaw | ConvertFrom-Json
if(-not $taskData.success){throw $taskData.error}
[IO.File]::WriteAllText($taskTarget,($taskRaw -join "`n"),[Text.UTF8Encoding]::new($false))
$taskData.data.result | Select-Object before,afterCenterButton,afterInspectorPlayEvent,afterCenterResumeButton | ConvertTo-Json -Compress -Depth 5
