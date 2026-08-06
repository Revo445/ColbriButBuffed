# Clean non-Colibri experiment models and ensure Colibri GLM-5.2 abliterated is installed.
#
# Reality check: the ONLY public Colibri-format abliterated MoE on Hugging Face is
#   leonid-k/GLM-5.2-abliterated-int4-colibri  (~350 GB)
# DeepSeek GGUF / ComfyUI NVFP4 do NOT run in coli. There is no smaller abliterated
# Colibri container that is still "frontier MoE" class.

param(
    [string]$GlmDir = "C:\glm52_ablit",
    [string]$Repo = "leonid-k/GLM-5.2-abliterated-int4-colibri",
    [switch]$SkipDownload,
    [switch]$RemoveComfyModels
)

$ErrorActionPreference = "Stop"

function Find-Hf {
    $cmd = Get-Command hf -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\Scripts\hf.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\Scripts\hf.exe")
    )) { if (Test-Path $p) { return $p } }
    return $null
}

function Remove-DirIfExists([string]$path, [string]$label) {
    if (-not (Test-Path $path)) {
        Write-Host "  skip (missing): $path"
        return
    }
    $gb = 0.0
    try {
        $gb = [math]::Round(((Get-ChildItem $path -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object Length -Sum).Sum) / 1GB, 1)
    } catch { }
    Write-Host "  deleting $label ($path) ~$gb GB …" -ForegroundColor Yellow
    Remove-Item -LiteralPath $path -Recurse -Force
    Write-Host "  deleted."
}

Write-Host "==> Colibri abliterated cleanup / restore" -ForegroundColor Cyan
Write-Host "    Target GLM dir: $GlmDir"
Write-Host "    HF repo       : $Repo"
Write-Host ""

# Stop coli so files unlock
$coli = "C:\Users\Isaac Sherer\Projects\colibri-lowspec\c\coli"
if (Test-Path $coli) {
    Write-Host "==> Stopping coli serve…"
    try { python $coli stop --port 8000 2>$null } catch { }
}

Write-Host "==> Removing non-Colibri experiment models"
Remove-DirIfExists "C:\deepseek_v4_flash" "DeepSeek GGUF"
Remove-DirIfExists "C:\glm52_i4" "stock GLM (if present)"
# Partial/wrong downloads sometimes land here:
Remove-DirIfExists "C:\Users\Isaac Sherer\Projects\colibri-lowspec\models" "repo models scratch"

if ($RemoveComfyModels) {
    Remove-DirIfExists "C:\ComfyUI\models\text_encoders" "Comfy text encoders"
    Remove-DirIfExists "C:\ComfyUI\models\diffusion_models" "Comfy diffusion"
    Remove-DirIfExists "C:\ComfyUI\models\vae" "Comfy VAE"
}

# Decide whether GLM abliterated is complete enough
$needDownload = $true
if (Test-Path (Join-Path $GlmDir "config.json")) {
    $st = @(Get-ChildItem $GlmDir -Filter "*.safetensors" -ErrorAction SilentlyContinue).Count
    $gb = [math]::Round(((Get-ChildItem $GlmDir -Recurse -File -Force -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum).Sum) / 1GB, 1)
    Write-Host "==> Found $GlmDir — $st safetensors, ~$gb GB"
    if ($st -ge 100 -and $gb -ge 300) {
        Write-Host "    Looks complete — keeping it (Colibri abliterated GLM)."
        $needDownload = $false
    } else {
        Write-Host "    Incomplete — will re-download."
        Remove-DirIfExists $GlmDir "incomplete GLM abliterated"
    }
} else {
    Write-Host "==> No complete GLM abliterated at $GlmDir"
}

if ($SkipDownload) {
    Write-Host "==> SkipDownload set — not fetching."
    exit 0
}

if (-not $needDownload) {
    Write-Host ""
    Write-Host "Ready. Run:" -ForegroundColor Green
    Write-Host "  cd C:\Users\Isaac Sherer\Projects\colibri-lowspec\c"
    Write-Host "  python coli chat --model $GlmDir --policy lowspec"
    exit 0
}

$freeGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Write-Host "==> C: free: $freeGB GB (need ~360+ GB)"
if ($freeGB -lt 360) {
    throw "Not enough free space to download GLM abliterated (~350 GB). Free disk first."
}

$hf = Find-Hf
if (-not $hf) {
    python -m pip install -U "huggingface_hub[hf_transfer]"
    $hf = Find-Hf
    if (-not $hf) { throw "hf.exe not found" }
}

New-Item -ItemType Directory -Force -Path $GlmDir | Out-Null
$env:HF_HUB_ENABLE_HF_TRANSFER = "1"
Write-Host "==> Downloading $Repo -> $GlmDir (resume-safe, hours)…"
& $hf download $Repo --local-dir $GlmDir
if ($LASTEXITCODE -ne 0) { throw "hf download failed" }

$st = @(Get-ChildItem $GlmDir -Filter "*.safetensors" -ErrorAction SilentlyContinue).Count
$gb = [math]::Round(((Get-ChildItem $GlmDir -Recurse -File -Force -ErrorAction SilentlyContinue |
    Measure-Object Length -Sum).Sum) / 1GB, 1)
Write-Host ""
Write-Host "Done: $st safetensors, ~$gb GB at $GlmDir" -ForegroundColor Green
Write-Host "  cd C:\Users\Isaac Sherer\Projects\colibri-lowspec\c"
Write-Host "  python coli doctor --model $GlmDir --policy lowspec"
Write-Host "  python coli chat   --model $GlmDir --policy lowspec"
Write-Host "Or desktop\dist\StartColbriButBuffed.exe"
