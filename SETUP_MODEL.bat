@echo off
setlocal
cd /d "%~dp0"
where ollama >nul 2>&1
if errorlevel 1 goto missing
echo This downloads Qwen3 8B to Ollama's model folder. Internet is needed.
echo If Ollama is not running, open the Ollama app first.
ollama pull qwen3:8b
if errorlevel 1 goto failed
echo Model download complete. You can now run START_JARVIS.bat.
pause
exit /b 0
:missing
echo Install Ollama from https://ollama.com/download/windows then open a new terminal or run this file again.
pause
exit /b 1
:failed
echo The download did not finish. Check Ollama, your connection, and free disk space; then run this file again.
pause
exit /b 1
