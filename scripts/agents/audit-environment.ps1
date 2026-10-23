param([string]$ProjectRoot = (Resolve-Path "$PSScriptRoot/../..").Path)
$ErrorActionPreference = 'Stop'
$taskOs = Get-CimInstance Win32_OperatingSystem
$taskCpu = Get-CimInstance Win32_Processor
$taskGpu = Get-CimInstance Win32_VideoController
$taskPython = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
$taskPackages = if (Test-Path -LiteralPath $taskPython) {
    & $taskPython -c "import importlib.metadata as m,json; names=['Pillow','numpy','torch','onnxruntime','onnxruntime-directml','diffusers','transformers']; versions={d.metadata['Name'].lower():d.version for d in m.distributions()}; print(json.dumps({n:versions.get(n.lower()) for n in names}))" | ConvertFrom-Json
}
$taskCommands = @{}
foreach ($taskName in @('node','rustc','cargo','docker','wsl','ollama','llama-server','ffmpeg','ffprobe')) {
    $taskCommand = Get-Command $taskName -ErrorAction SilentlyContinue
    $taskCommands[$taskName] = if ($taskCommand) { $taskCommand.Source } else { $null }
}
$taskWsl = if ($taskCommands['wsl']) {
    try { ((& wsl.exe --list --quiet 2>&1 | Out-String) -replace "`0", '').Trim() }
    catch { 'WSL command exists, but no functional distribution was detected.' }
} else { 'Command not found' }
$taskFfmpeg = @(Get-ChildItem -LiteralPath (Join-Path $ProjectRoot '.codex-runtime/ffmpeg') -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
$taskModels = @{}
foreach ($taskFolder in @((Join-Path $env:USERPROFILE '.ollama/models'),(Join-Path $env:USERPROFILE '.cache/huggingface/hub'))) {
    $taskModels[$taskFolder] = @{ exists=(Test-Path -LiteralPath $taskFolder); directoryCount=@(Get-ChildItem -LiteralPath $taskFolder -Directory -ErrorAction SilentlyContinue).Count }
}
[ordered]@{
    checkedAt=(Get-Date -Format o)
    operatingSystem=@{name=$taskOs.Caption;version=$taskOs.Version;architecture=$taskOs.OSArchitecture}
    cpu=@{name=$taskCpu.Name;cores=$taskCpu.NumberOfCores;logicalProcessors=$taskCpu.NumberOfLogicalProcessors}
    ram=@{totalBytes=[long]$taskOs.TotalVisibleMemorySize*1024;freeBytes=[long]$taskOs.FreePhysicalMemory*1024}
    graphics=@($taskGpu | ForEach-Object { @{name=$_.Name;adapterRamReportedBytes=[long]$_.AdapterRAM;driverVersion=$_.DriverVersion} })
    disk=@(Get-PSDrive -PSProvider FileSystem | Where-Object Name -EQ 'C' | Select-Object Name,Used,Free)
    commands=$taskCommands
    pythonVersion=if(Test-Path -LiteralPath $taskPython){(& $taskPython --version)}else{$null}
    nodeVersion=(& node --version)
    ffmpegPrivateExecutables=$taskFfmpeg
    packages=$taskPackages
    modelDirectories=$taskModels
    wsl=$taskWsl
    note='AdapterRAM on integrated graphics is not proof of dedicated VRAM. CUDA/DirectML inference was not benchmarked.'
} | ConvertTo-Json -Depth 5
