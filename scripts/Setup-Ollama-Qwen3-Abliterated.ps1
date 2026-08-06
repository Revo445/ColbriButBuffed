# Download abliterated Qwen3-30B-A3B via Ollama (fits ~32 GB RAM).
# Model: huihui_ai/qwen3-abliterated:30b-a3b  (~18–19 GB Q4)
# Does NOT touch GLM / Colibri.

param(
    [string]$Model = "huihui_ai/qwen3-abliterated:30b-a3b",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

Write-Host "==> Abliterated Qwen3-30B-A3B (Ollama)" -ForegroundColor Cyan
Write-Host "    Tag: $Model"
Write-Host "    ~19 GB download · MoE · ~3B active · abliterated by huihui-ai"
Write-Host ""

if (-not (Get-Command ollama -ErrorAction SilentlyContinue) -and -not $SkipInstall) {
    Write-Host "==> Installing Ollama…"
    $installer = Join-Path $env:TEMP "OllamaSetup.exe"
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $installer
    Start-Process -FilePath $installer -Wait
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "ollama not on PATH. Install from https://ollama.com/download then re-run."
}

Write-Host "==> Pulling $Model …"
ollama pull $Model
if ($LASTEXITCODE -ne 0) { throw "ollama pull failed" }

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host "  ollama run $Model"
Write-Host ""
Write-Host "ColbriChat API: http://127.0.0.1:11434/v1"
Write-Host "  Probe → select the huihui qwen3-abliterated model"
