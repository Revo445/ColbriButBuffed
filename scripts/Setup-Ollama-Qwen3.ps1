# Install/use Ollama with Qwen3-30B-A3B on this machine (~32 GB RAM, AMD, no NVIDIA).
# Does NOT touch C:\glm52_ablit. Does NOT use Colibri.

param(
    [string]$Model = "qwen3:30b",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Write-Host "==> Ollama setup for ColbriButBuffed companion chat" -ForegroundColor Cyan
Write-Host "    Model: $Model  (~19 GB download, fits ~32 GB RAM)"
Write-Host "    Why: MoE with ~3B active params — much faster than GLM disk-streaming on CPU/AMD"
Write-Host ""

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama -and -not $SkipInstall) {
    Write-Host "==> Installing Ollama for Windows…"
    $installer = Join-Path $env:TEMP "OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer
    Start-Process -FilePath $installer -Wait
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $ollama = Get-Command ollama -ErrorAction SilentlyContinue
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "ollama not on PATH. Install from https://ollama.com/download then re-run."
}

Write-Host "==> Pulling $Model (resume-safe)…"
ollama pull $Model
if ($LASTEXITCODE -ne 0) { throw "ollama pull failed" }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "Chat in terminal:"
Write-Host "  ollama run $Model"
Write-Host ""
Write-Host "OpenAI-compatible API (for ColbriChat):"
Write-Host "  base URL = http://127.0.0.1:11434/v1"
Write-Host "  (Ollama serves this while running; no separate coli serve)"
Write-Host ""
Write-Host "Smoke test:"
Write-Host "  ollama run $Model `"Write a Python function that binary-searches a sorted list.`""
