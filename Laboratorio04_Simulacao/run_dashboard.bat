@echo off
echo ========================================================
echo  Iniciando Dashboard - Laboratorio 04 (Lab04S01)
echo ========================================================
cd /d "%~dp0"

IF EXIST ".venv\Scripts\streamlit.exe" (
    ".venv\Scripts\streamlit.exe" run dashboard.py
) ELSE (
    streamlit run dashboard.py
)
pause
