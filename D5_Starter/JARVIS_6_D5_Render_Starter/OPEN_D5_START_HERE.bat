@echo off
setlocal
cd /d "%~dp0"
echo ================================================
echo JARVIS 6 -- D5 Render starter
 echo ================================================
echo.
echo Opening 3D imports folder and setup instructions.
echo You must install / launch D5 Render yourself.
echo No installer or admin permissions are run by this file.
start "" "%~dp001_IMPORT_INTO_D5"
start "" "%~dp0START_HERE.txt"
echo.
echo Official D5 download: https://www.d5render.com/download
echo.
pause
