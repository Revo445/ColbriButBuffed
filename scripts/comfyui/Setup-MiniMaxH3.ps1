# Setup ComfyUI for MiniMax-H3 + Heretic NVFP4 text encoder (Windows).
# See docs/comfyui-minimax-h3.md

param(
    [string]$ComfyRoot = "C:\ComfyUI",
    [switch]$ModelsOnly,
    [switch]$IncludeR2V,
    [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }

function Ensure-Dir($path) {
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}

function Find-Python {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe")
    ) | Where-Object { $_ -and (Test-Path $_) }
    if (-not $candidates) { throw "Python not found on PATH. Install Python 3.11+ from python.org" }
    return $candidates[0]
}

function Find-Hf {
    $hf = Get-Command hf -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    if ($hf) { return $hf }
    $scripts = Join-Path (Split-Path (Find-Python)) "Scripts\hf.exe"
    if (Test-Path $scripts) { return $scripts }
    $alt = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\Scripts\hf.exe"
    if (Test-Path $alt) { return $alt }
    return $null
}

function Invoke-HfDownload {
    param([string]$Repo, [string]$File, [string]$LocalDir)
    Ensure-Dir $LocalDir
    $dest = Join-Path $LocalDir (Split-Path $File -Leaf)
    if (Test-Path $dest) {
        $size = (Get-Item $dest).Length
        if ($size -gt 1MB) {
            Write-Host "  skip (exists): $dest ($([math]::Round($size/1GB,2)) GB)"
            return
        }
    }
    $hf = Find-Hf
    if (-not $hf) {
        Write-Step "Installing huggingface_hub[hf_transfer]"
        & (Find-Python) -m pip install -U "huggingface_hub[hf_transfer]"
        $hf = Find-Hf
        if (-not $hf) { throw "hf.exe still missing after pip install" }
    }
    $env:HF_HUB_ENABLE_HF_TRANSFER = "1"
    Write-Host "  downloading $Repo :: $File"
    Write-Host "  -> $LocalDir"
    & $hf download $Repo --include $File --local-dir $LocalDir
    if ($LASTEXITCODE -ne 0) { throw "hf download failed for $File (exit $LASTEXITCODE)" }
}

$py = Find-Python
Write-Host "Python: $py"
Write-Host "ComfyUI root: $ComfyRoot"

if (-not $ModelsOnly) {
    Write-Step "Clone / update ComfyUI"
    Ensure-Dir (Split-Path $ComfyRoot -Parent)
    if (-not (Test-Path (Join-Path $ComfyRoot ".git"))) {
        git clone https://github.com/comfyanonymous/ComfyUI.git $ComfyRoot
    } else {
        Push-Location $ComfyRoot
        git pull --ff-only
        Pop-Location
    }

    if (-not $SkipVenv) {
        Write-Step "Python venv + requirements"
        $venvPy = Join-Path $ComfyRoot "venv\Scripts\python.exe"
        if (-not (Test-Path $venvPy)) {
            & $py -m venv (Join-Path $ComfyRoot "venv")
        }
        & $venvPy -m pip install -U pip wheel
        & $venvPy -m pip install -r (Join-Path $ComfyRoot "requirements.txt")
        # Torch CUDA wheel: best-effort; user may already have a matching torch.
        Write-Host "If you have an NVIDIA GPU, install a CUDA torch build from https://pytorch.org matching your driver."
    }
}

Write-Step "Model directories"
$models = Join-Path $ComfyRoot "models"
$te = Join-Path $models "text_encoders"
$diff = Join-Path $models "diffusion_models"
$vae = Join-Path $models "vae"
Ensure-Dir $te; Ensure-Dir $diff; Ensure-Dir $vae

Write-Step "Heretic NVFP4 text encoder (~15.7 GB)"
Invoke-HfDownload `
    -Repo "sakamakismile/Qwen3-VL-32B-Heretic-MiniMax-H3-NVFP4" `
    -File "qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors" `
    -LocalDir $te

Write-Step "MiniMax-H3 pruned diffusion T2V/I2V (~21 GB)"
# Download into models/ so Hugging Face keeps diffusion_models/ prefix, then ensure flat path.
Invoke-HfDownload `
    -Repo "Comfy-Org/MiniMax-H3" `
    -File "diffusion_models/minimax_h3_fl2va_pruned_int8_convrot.safetensors" `
    -LocalDir $models
$nested = Join-Path $models "diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors"
$flat = Join-Path $diff "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
if ((Test-Path $nested) -and ($nested -ne $flat)) {
    # already in the right folder when LocalDir=models
} elseif (Test-Path (Join-Path $diff "diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors")) {
    Move-Item (Join-Path $diff "diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors") $flat -Force
}

if ($IncludeR2V) {
    Write-Step "MiniMax-H3 pruned diffusion R2V (~21 GB)"
    Invoke-HfDownload `
        -Repo "Comfy-Org/MiniMax-H3" `
        -File "diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors" `
        -LocalDir $models
}

Write-Step "VAEs"
Invoke-HfDownload -Repo "Comfy-Org/MiniMax-H3" -File "vae/minimax_h3_video_vae_fp16.safetensors" -LocalDir $models
Invoke-HfDownload -Repo "Comfy-Org/MiniMax-H3" -File "vae/minimax_h3_audio_vae_fp32.safetensors" -LocalDir $models

Write-Step "Sanity check"
$required = @(
    (Join-Path $te "qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors"),
    (Join-Path $diff "minimax_h3_fl2va_pruned_int8_convrot.safetensors"),
    (Join-Path $vae "minimax_h3_video_vae_fp16.safetensors"),
    (Join-Path $vae "minimax_h3_audio_vae_fp32.safetensors")
)
$missing = @()
foreach ($p in $required) {
    if (-not (Test-Path $p)) { $missing += $p } else {
        Write-Host ("  OK {0:N2} GB  {1}" -f ((Get-Item $p).Length/1GB), $p)
    }
}
if ($missing.Count) {
    Write-Host "Missing:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  $_" }
    throw "Download incomplete"
}

$launcher = Join-Path $ComfyRoot "run_nvidia_gpu.bat"
if (-not (Test-Path $launcher)) {
    @"
@echo off
cd /d "%~dp0"
if exist venv\Scripts\python.exe (
  venv\Scripts\python.exe main.py --listen 127.0.0.1 --port 8188
) else (
  python main.py --listen 127.0.0.1 --port 8188
)
"@ | Set-Content -Encoding ASCII (Join-Path $ComfyRoot "Start-MiniMaxH3.bat")
}

Write-Host "`nDone." -ForegroundColor Green
Write-Host "1) Start:  scripts\comfyui\Start-ComfyUI.bat   (or $ComfyRoot\Start-MiniMaxH3.bat)"
Write-Host "2) Open:   http://127.0.0.1:8188"
Write-Host "3) Template Library -> Video -> MiniMax H3 T2V"
Write-Host "4) CLIPLoader clip_name = qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors, type = minimax"
Write-Host "Docs: docs\comfyui-minimax-h3.md"
