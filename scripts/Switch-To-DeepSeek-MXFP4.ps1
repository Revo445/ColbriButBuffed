# Remove Colibri GLM-5.2 abliterated and download Huihui DeepSeek-V4-Flash MXFP4 GGUF.
# File: DeepSeek-V4-Flash-Q4-mxfp4-0731.gguf (~145 GB)
# This is GGUF — it does NOT run in ColbriButBuffed/coli. Use llama.cpp or antirez/ds4.

param(
    [string]$GlmDir = "C:\glm52_ablit",
    [string]$OutDir = "C:\deepseek_v4_flash",
    [string]$Quant = "DeepSeek-V4-Flash-Q4-mxfp4-0731.gguf",
    [switch]$KeepGlm,
    [switch]$DownloadOnly
)

$ErrorActionPreference = "Stop"
$Repo = "huihui-ai/Huihui-DeepSeek-V4-Flash-0731-abliterated-GGUF"

function Find-Hf {
    $cmd = Get-Command hf -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\Scripts\hf.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\Scripts\hf.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\Scripts\hf.exe")
    )
    foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
    return $null
}

Write-Host "==> DeepSeek-V4-Flash MXFP4 swap" -ForegroundColor Cyan
Write-Host "    Remove GLM dir : $GlmDir"
Write-Host "    Download to    : $OutDir\$Quant"
Write-Host "    HF repo        : $Repo"
Write-Host ""

# Stop coli serve if present (frees handles on the model dir).
$coli = "C:\Users\Isaac Sherer\Projects\colibri-lowspec\c\coli"
if (Test-Path $coli) {
    Write-Host "==> Stopping coli serve (if running)…"
    try {
        python $coli stop --port 8000 2>$null
    } catch { }
}

if (-not $KeepGlm -and -not $DownloadOnly) {
    if (Test-Path $GlmDir) {
        $gb = [math]::Round(((Get-ChildItem $GlmDir -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object Length -Sum).Sum) / 1GB, 1)
        Write-Host "==> Removing $GlmDir (~$gb GB)…" -ForegroundColor Yellow
        Remove-Item -LiteralPath $GlmDir -Recurse -Force
        Write-Host "    Deleted."
    } else {
        Write-Host "==> GLM dir not found ($GlmDir) — skip delete."
    }
} else {
    Write-Host "==> Keeping GLM dir (KeepGlm/DownloadOnly)."
}

$freeGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Write-Host "==> C: free space: $freeGB GB (need ~150 GB for MXFP4 GGUF)"
if ($freeGB -lt 150) {
    throw "Not enough free space on C: ($freeGB GB). Free disk or set -OutDir to another drive."
}

$hf = Find-Hf
if (-not $hf) {
    Write-Host "==> Installing huggingface_hub…"
    python -m pip install -U "huggingface_hub[hf_transfer]"
    $hf = Find-Hf
    if (-not $hf) { throw "hf.exe not found after pip install" }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$dest = Join-Path $OutDir $Quant
if ((Test-Path $dest) -and ((Get-Item $dest).Length -gt 100GB)) {
    Write-Host "==> Already present: $dest ($([math]::Round((Get-Item $dest).Length/1GB,1)) GB)"
} else {
    $env:HF_HUB_ENABLE_HF_TRANSFER = "1"
    Write-Host "==> Downloading $Quant (~145 GB). Resume-safe if interrupted."
    & $hf download $Repo --include $Quant --local-dir $OutDir
    if ($LASTEXITCODE -ne 0) { throw "hf download failed (exit $LASTEXITCODE)" }
}

if (-not (Test-Path $dest)) {
    # Some hf versions nest unexpectedly
    $alt = Get-ChildItem $OutDir -Recurse -Filter $Quant -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($alt) { $dest = $alt.FullName }
}

if (-not (Test-Path $dest)) { throw "Download finished but $Quant not found under $OutDir" }

Write-Host ""
Write-Host "Done: $dest ($([math]::Round((Get-Item $dest).Length/1GB,1)) GB)" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: This GGUF does NOT run in ColbriButBuffed / coli." -ForegroundColor Yellow
Write-Host "Use latest llama.cpp or antirez/ds4 (ds4f-mxfp4 branch for MXFP4)."
Write-Host ""
Write-Host "Example (llama.cpp server, CPU/mmap — slow on 32 GB RAM):"
Write-Host "  llama-server -m `"$dest`" -c 8192 --host 127.0.0.1 --port 8080 --jinja"
Write-Host ""
Write-Host "Example (ds4, NVIDIA):"
Write-Host "  .\ds4 -m `"$dest`" --ctx 32768"
Write-Host ""
Write-Host "Point ColbriChat / any OpenAI client at http://127.0.0.1:8080/v1 after llama-server is up."
