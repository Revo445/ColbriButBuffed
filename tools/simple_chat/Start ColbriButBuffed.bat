@echo off
title Start ColbriButBuffed
cd /d "%~dp0"

REM One-click: start coli serve (lowspec) + open chat UI
REM Preferred built exe locations (built on your Windows PC):
REM   ..\..\desktop\dist\StartColbriButBuffed.exe
REM   ..\..\desktop\dist\ColbriChat.exe

set "START_EXE=%~dp0..\..\desktop\dist\StartColbriButBuffed.exe"
if exist "%START_EXE%" (
  start "" "%START_EXE%"
  exit /b 0
)

set "LOCAL_START=%~dp0dist\StartColbriButBuffed.exe"
if exist "%LOCAL_START%" (
  start "" "%LOCAL_START%"
  exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Build the starter on Windows:
  echo   cd tools\simple_chat
  echo   python -m pip install pyinstaller
  echo   python -m PyInstaller --noconfirm --onefile --windowed --name StartColbriButBuffed start_colbri.py
  echo   copy dist\StartColbriButBuffed.exe ..\..\desktop\dist\
  pause
  exit /b 1
)

start "" pythonw "%~dp0start_colbri.py"
exit /b 0
