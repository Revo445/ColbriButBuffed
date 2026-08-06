@echo off
title ComfyUI MiniMax-H3
set "COMFY=C:\ComfyUI"
if not "%COMFYUI_ROOT%"=="" set "COMFY=%COMFYUI_ROOT%"

if not exist "%COMFY%\main.py" (
  echo ComfyUI not found at %COMFY%
  echo Run: powershell -ExecutionPolicy Bypass -File "%~dp0Setup-MiniMaxH3.ps1"
  pause
  exit /b 1
)

cd /d "%COMFY%"
if exist "venv\Scripts\python.exe" (
  start "" http://127.0.0.1:8188
  "venv\Scripts\python.exe" main.py --listen 127.0.0.1 --port 8188
) else (
  start "" http://127.0.0.1:8188
  python main.py --listen 127.0.0.1 --port 8188
)
