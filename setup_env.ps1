# CodeSentinel — isolated Python environment setup (PowerShell)
# Usage:  .\setup_env.ps1
# Then:   .\.venv\Scripts\Activate.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$Python = "py"
$PythonArgs = @("-3")

Write-Host "==> CodeSentinel environment setup" -ForegroundColor Cyan
Write-Host "    Project: $ProjectRoot"

# Resolve Python launcher
try {
    & $Python @PythonArgs -c "import sys; print(sys.version)" | Out-Null
} catch {
    Write-Error "Python 3 not found. Install Python 3.11+ and ensure 'py' launcher is available."
}

# Create virtual environment
if (-not (Test-Path $VenvPath)) {
    Write-Host "==> Creating virtual environment at .venv" -ForegroundColor Yellow
    & $Python @PythonArgs -m venv $VenvPath
} else {
    Write-Host "==> Virtual environment already exists" -ForegroundColor Green
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "venv python not found at $VenvPython"
}

# Upgrade pip inside venv (avoids global PATH script warnings)
Write-Host "==> Upgrading pip inside .venv" -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip

# Install pinned dependencies (protobuf aligned for LangChain + Google)
Write-Host "==> Installing dependencies from backend/requirements.txt" -ForegroundColor Yellow
& $VenvPip install -r (Join-Path $ProjectRoot "backend\requirements.txt")

Write-Host ""
Write-Host "==> Setup complete." -ForegroundColor Green
Write-Host "    Activate:  .\.venv\Scripts\Activate.ps1"
Write-Host "    Validate:  .\.venv\Scripts\python.exe tests\validate_p1.py"
Write-Host "    Run API:   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload"
