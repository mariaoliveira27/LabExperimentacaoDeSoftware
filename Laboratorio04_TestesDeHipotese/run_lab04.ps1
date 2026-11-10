# Execução em comando único a partir da pasta raiz do Laboratório 04
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir "dashboard")
& ".\run_dashboard.ps1"
