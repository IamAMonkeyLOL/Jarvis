@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pip install streamlit psutil
) else (
  py -m pip install --user streamlit psutil
)
pause
