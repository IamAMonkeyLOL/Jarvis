$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
py -m PyInstaller --noconfirm --clean --onefile --windowed --name jarvisd --collect-all webview main.py
Copy-Item -LiteralPath "$projectRoot\dist\jarvisd.exe" -Destination "$projectRoot\jarvisd.exe" -Force
Write-Host "Created $projectRoot\jarvisd.exe"
