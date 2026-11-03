# Script de execução em comando único para o Dashboard do Lab 04 (PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando Dashboard - Laboratório 04 (Lab04S01)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$PythonExe = "python"
$VenvCandidate = Join-Path $ScriptDir "..\.venv\Scripts\python.exe"
if (Test-Path $VenvCandidate) {
    $PythonExe = $VenvCandidate
}

$DataFile = Join-Path $ScriptDir "data\dados.json"
if (-not (Test-Path $DataFile)) {
    Write-Host "[INFO] Gerando dados analíticos e modelos..." -ForegroundColor Yellow
    & $PythonExe gerar_dashboard.py
}

Write-Host "[INFO] Abrindo navegador em http://localhost:8000 ..." -ForegroundColor Green
Start-Process "http://localhost:8000"

Write-Host "[INFO] Servidor HTTP local ativo na porta 8000. Pressione Ctrl+C para encerrar." -ForegroundColor Gray
& $PythonExe -m http.server 8000
