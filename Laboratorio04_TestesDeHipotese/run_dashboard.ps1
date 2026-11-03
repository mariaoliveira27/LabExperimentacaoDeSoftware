# Script de execução em comando único para o Dashboard do Lab04 (PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando Dashboard - Laboratório 04 (Lab04S01)" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$VenvStreamlit = Join-Path $ScriptDir ".venv\Scripts\streamlit.exe"

if (Test-Path $VenvStreamlit) {
    & $VenvStreamlit run dashboard.py
} else {
    streamlit run dashboard.py
}
