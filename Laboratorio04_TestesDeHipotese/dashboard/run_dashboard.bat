@echo off
echo ========================================================
echo   Iniciando Dashboard - Laboratorio 04 (Lab04S01)
echo ========================================================
cd /d "%~dp0"

IF NOT EXIST "data\dados.json" (
    echo [INFO] Gerando dados analiticos e graficos...
    IF EXIST "..\.venv\Scripts\python.exe" (
        "..\.venv\Scripts\python.exe" gerar_dashboard.py
    ) ELSE (
        python gerar_dashboard.py
    )
)

echo [INFO] Abrindo navegador em http://localhost:8000 ...
start http://localhost:8000

IF EXIST "..\.venv\Scripts\python.exe" (
    "..\.venv\Scripts\python.exe" -m http.server 8000
) ELSE (
    python -m http.server 8000
)
