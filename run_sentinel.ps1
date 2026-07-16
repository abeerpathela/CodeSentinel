# CodeSentinel - 1-Click Sentinel Command Center Launcher
# Usage: .\run_sentinel.ps1 [-RebuildUI]

param(
    [switch]$RebuildUI
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CodeSentinel - Command Center Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (-not (Test-Path "$ProjectRoot\.venv\Scripts\Activate.ps1")) {
    Write-Host "==> Bootstrapping Python environment..." -ForegroundColor Yellow
    & "$ProjectRoot\setup_env.ps1"
}

Push-Location "$ProjectRoot\frontend"
if (-not (Test-Path "node_modules")) {
    Write-Host "==> Installing frontend dependencies (React Three Fiber)..." -ForegroundColor Yellow
    npm install
}

$DistPath = "$ProjectRoot\frontend\dist"
$NeedsBuild = $RebuildUI -or -not (Test-Path $DistPath)

if (-not $NeedsBuild) {
    $srcNewer = Get-ChildItem -Path "$ProjectRoot\frontend\src" -Recurse -File |
        Where-Object { $_.LastWriteTime -gt (Get-Item $DistPath).LastWriteTime }
    if ($srcNewer) { $NeedsBuild = $true }
}

if ($NeedsBuild) {
    Write-Host "==> Building Command Center UI (production dist/)..." -ForegroundColor Yellow
    npm run build
    if (-not (Test-Path $DistPath)) {
        Write-Error "Frontend build failed — dist/ not found."
    }
    Write-Host "==> UI built: frontend/dist" -ForegroundColor Green
} else {
    Write-Host "==> UI dist/ up to date" -ForegroundColor Green
}
Pop-Location

Write-Host "==> Activating virtual environment" -ForegroundColor Green
. "$ProjectRoot\.venv\Scripts\Activate.ps1"

Write-Host "==> Starting FastAPI backend -> http://127.0.0.1:8000" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$ProjectRoot'; .\.venv\Scripts\Activate.ps1; python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "==> Starting Vite dev server -> http://127.0.0.1:5173" -ForegroundColor Green
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$ProjectRoot\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Landing:    http://127.0.0.1:5173  (Splash -> Hero -> Command Center)" -ForegroundColor Cyan
Write-Host "API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "Fixtures:   http://127.0.0.1:8000/analytics/fixtures" -ForegroundColor Cyan
Write-Host "Export:     http://127.0.0.1:8000/analytics/export" -ForegroundColor Cyan
Write-Host "Gauntlet:   python tests/gauntlet.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Command Center live. Use -RebuildUI to force frontend production build." -ForegroundColor Yellow
