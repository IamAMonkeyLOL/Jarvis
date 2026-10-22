@echo off

echo Starting Jarvis...
echo.

.venv\Scripts\python.exe -m streamlit run app.py

echo.
echo ==============================
echo Jarvis stopped or crashed.
echo ==============================
echo.
pause 