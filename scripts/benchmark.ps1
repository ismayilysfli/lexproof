param(
    [switch]$Offline
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot "backend/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Project venv not found. Follow the backend setup commands in README.md."
}

$previousOffline = $env:HF_HUB_OFFLINE
Push-Location $projectRoot
try {
    if ($Offline) { $env:HF_HUB_OFFLINE = "1" }
    & $pythonPath -m pytest -q -m benchmark
    $benchmarkExitCode = $LASTEXITCODE
}
finally {
    $env:HF_HUB_OFFLINE = $previousOffline
    Pop-Location
}
exit $benchmarkExitCode
