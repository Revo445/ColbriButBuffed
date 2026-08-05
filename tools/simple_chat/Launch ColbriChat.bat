@echo off
title ColbriButBuffed Chat
cd /d "%~dp0"

REM Chat UI only — does NOT start the engine.
REM To auto-start GLM-5.2 (serve + chat), use "Start ColbriButBuffed.bat" instead.

set "EXE=%~dp0dist\ColbriChat.exe"
if not exist "%EXE%" set "EXE=%~dp0..\..\desktop\dist\ColbriChat.exe"
set "PY=%~dp0colbri_chat.py"

if exist "%EXE%" (
  start "" "%EXE%"
  exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found and ColbriChat.exe is missing.
  echo Build with: python -m pip install pyinstaller ^&^& python -m PyInstaller --noconfirm --onefile --windowed --name ColbriChat colbri_chat.py
  pause
  exit /b 1
)

start "" pythonw "%PY%"
exit /b 0
