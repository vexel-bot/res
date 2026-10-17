param([switch]$StatusOnly)
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$taskRuntime = Join-Path $taskRoot '.codex-runtime\craft\local'
$taskMarker = Join-Path $taskRuntime 'processes.json'
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'workers\craft\sources.lock.json'))) { throw 'Run from the qualified Craft checkout.' }
if (Test-Path -LiteralPath $taskMarker) {
    $taskPrevious = Get-Content -LiteralPath $taskMarker -Raw | ConvertFrom-Json
    $taskAlive = @($taskPrevious.processes | Where-Object {
        $taskProcess = Get-Process -Id $_.pid -ErrorAction SilentlyContinue
        $taskRecordedStart = if ($_.startedAt -is [datetime]) { $_.startedAt.ToUniversalTime() }
            else { [DateTimeOffset]::Parse([string]$_.startedAt, [Globalization.CultureInfo]::InvariantCulture).UtcDateTime }
        $taskProcess -and $taskProcess.StartTime.ToUniversalTime() -eq $taskRecordedStart
    })
    if ($taskAlive.Count -eq 3) { Write-Output 'Clicko Craft is running at http://127.0.0.1:3000'; return }
    if ($taskAlive.Count -gt 0) { throw 'A partial local runtime remains active. Inspect the recorded processes before restarting.' }
}
if ($StatusOnly) { Write-Output 'Clicko Craft local runtime is stopped.'; return }
foreach ($taskPort in @(3000,8000)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $taskPort -ErrorAction SilentlyContinue) { throw "Port $taskPort is already in use. No existing process was stopped." }
}
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot 'dist\server.js'))) { throw 'Build the checkout with npm run build first.' }
New-Item -ItemType Directory -Path $taskRuntime -Force | Out-Null
$taskContainer = 'clicko-craft-local-redis'
$taskOwnedBroker = docker ps -a --filter "name=^/$taskContainer$" --filter 'label=clicko.managed=craft-studios-local' --format '{{.Names}}'
if ($taskOwnedBroker -eq $taskContainer) {
    docker start $taskContainer | Out-Null
} else {
    docker run --detach --name $taskContainer --label clicko.managed=craft-studios-local --memory 128m --cpus 0.25 --publish 127.0.0.1:6383:6379 --restart unless-stopped --mount type=volume,source=clicko-craft-local-redis,target=/data redis:8.2.1-alpine redis-server --appendonly yes --maxmemory 96mb --maxmemory-policy noeviction | Out-Null
}
if ($LASTEXITCODE -ne 0) { throw 'The dedicated local broker could not be started.' }
$taskVariables = @{
    ENVIRONMENT='development'; REDIS_URL='redis://127.0.0.1:6383/0'; CELERY_TASK_ALWAYS_EAGER='false'
    STUDIO_ISOLATED_QUEUES_ENABLED='false'; OPENAI_OUTBOUND_ENABLED='false'; OPENAI_VIDEO_GENERATION_ENABLED='false'
    STUDIO_GEMINI_ENABLED='false'; STUDIO_EDITING_AI_PLANNING_PROVIDER='none'; STUDIO_PRODUCTION_TEST_BUDGET_USD='0'
    PYTHONPATH='backend'; PORT='3000'; CLICKO_STUDIOS_ORIGIN='http://127.0.0.1:8000'; NODE_ENV='production'
    DATABASE_URL=('sqlite:///' + (Join-Path $taskRoot '.clicko-data\studios\records.sqlite').Replace('\','/'))
    STORAGE_PATH=(Join-Path $taskRoot '.clicko-data\studios\uploads')
}
$taskOldVariables = @{}
$taskProcesses = @()
try {
    foreach ($taskName in $taskVariables.Keys) {
        $taskOldVariables[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process')
        [Environment]::SetEnvironmentVariable($taskName, $taskVariables[$taskName], 'Process')
    }
    $taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $taskPython)) { $taskPython = (Get-Command python).Source }
    New-Item -ItemType Directory -Path (Join-Path $taskRoot '.clicko-data\studios') -Force | Out-Null
    $taskNode = (Get-Command node).Source
    foreach ($taskService in @(
        @{name='worker';file=$taskPython;arguments='-u -m celery -A app.celery_app:celery_app worker --pool=solo --concurrency=1 --queues=celery,studio.media.cpu --loglevel=INFO --without-gossip --without-mingle --without-heartbeat'},
        @{name='api';file=$taskPython;arguments='-u -m uvicorn app.studio_app:app --app-dir backend --host 127.0.0.1 --port 8000'},
        @{name='web';file=$taskNode;arguments='dist/server.js'}
    )) {
        $taskProcess = Start-Process -FilePath $taskService.file -ArgumentList $taskService.arguments -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskRuntime ($taskService.name+'.out.log')) -RedirectStandardError (Join-Path $taskRuntime ($taskService.name+'.err.log'))
        $taskProcesses += @{name=$taskService.name;pid=$taskProcess.Id;startedAt=$taskProcess.StartTime.ToUniversalTime().ToString('o')}
        @{project=$taskRoot;broker=$taskContainer;processes=$taskProcesses} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskMarker
    }
} finally {
    foreach ($taskName in $taskOldVariables.Keys) { [Environment]::SetEnvironmentVariable($taskName, $taskOldVariables[$taskName], 'Process') }
}
Write-Output 'Clicko Craft started at http://127.0.0.1:3000. Logs: .codex-runtime/craft/local'
