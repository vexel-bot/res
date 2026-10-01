$workerDirectory = $PSScriptRoot
$repositoryDirectory = Split-Path -Parent (Split-Path -Parent $workerDirectory)
$outputDirectory = Join-Path $repositoryDirectory 'benchmarks\studios\hybrid-generation\qualification-smoke-20260914'
& (Join-Path $workerDirectory 'prepare_qualification_host.ps1') -OutputDirectory $outputDirectory
