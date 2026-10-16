param([Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9-]+$')][string]$Stage)
$ErrorActionPreference = 'Stop'
$evidenceRoot = Join-Path $PSScriptRoot '../../docs/studios/research/editor-oss-20261002/temporal-matte-inspection-browser'
$targetPath = Join-Path $evidenceRoot ('ui-' + $Stage + '.json')
if (Test-Path -LiteralPath $targetPath) { throw 'Preserve an existing UI observation' }
$captureScript = @'
(() => {
  const section=document.querySelector('.editor-inspection');
  if(!section)throw new Error('actual inspector required');
  const bounds=section.getBoundingClientRect();
  const video=section.querySelector('video');
  const selected=section.querySelector('select[aria-label="Camada"]');
  const mask=section.querySelector('[aria-label="Máscara da camada"]');
  return {scope:'actual_browser_DOM_no_API_mock',url:location.href,
    observedAt:new Date().toISOString(),inspectorVisible:!!section.offsetParent&&bounds.width>0&&bounds.height>0,
    selectedLayer:selected?.value,selectedLayerLabel:selected?.selectedOptions[0]?.textContent,
    compositionFrame:section.querySelector('input[aria-label="Frame da composição"]')?.value,
    maskText:mask?.innerText??null,inspectorText:section.innerText,
    tracks:Array.from(section.querySelectorAll('table tbody tr')).map(row=>Array.from(row.cells).map(cell=>cell.innerText)),
    video:video?{src:video.currentSrc,readyState:video.readyState,currentTime:video.currentTime,
      paused:video.paused,duration:video.duration,videoWidth:video.videoWidth,videoHeight:video.videoHeight}:null};
})()
'@
$captureBase64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($captureScript))
$captureOutput = & agent-browser --session res-matte-inspection-20261004 --json eval -b $captureBase64
if ($LASTEXITCODE -ne 0) { throw 'Browser observation failed' }
$capture = $captureOutput | ConvertFrom-Json
if (!$capture.success -or !$capture.data.result.inspectorVisible) { throw 'Visible inspector evidence required' }
$captureOutput | Set-Content -LiteralPath $targetPath -Encoding utf8
@{ stage=$Stage; selected=$capture.data.result.selectedLayerLabel; frame=$capture.data.result.compositionFrame;
   maskPresent=($null -ne $capture.data.result.maskText); videoPresent=($null -ne $capture.data.result.video) } | ConvertTo-Json -Compress
