# Download Colibri-format abliterated GLM-5.2
# Requires ~400 GB free. Stock C:\glm52_i4 is also ~400 GB — free space first if needed.

$ErrorActionPreference = "Stop"
$OutDir = if ($args[0]) { $args[0] } else { "C:\glm52_ablit" }
$Repo = "leonid-k/GLM-5.2-abliterated-int4-colibri"
$Hf = Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.14-64\Scripts\hf.exe"

if (-not (Test-Path $Hf)) {
  Write-Host "hf.exe not found at $Hf — install huggingface_hub or fix the path." -ForegroundColor Yellow
  exit 1
}

$freeGB = [math]::Round((Get-PSDrive C).Free / 1GB, 1)
Write-Host "C: free space: $freeGB GB (need ~400 GB for a full download)"
if ($freeGB -lt 380) {
  Write-Host "Not enough free space. Move/delete C:\glm52_i4 (or pass another drive path)." -ForegroundColor Red
  Write-Host "Example: .\download_abliterated.ps1 E:\glm52_ablit" -ForegroundColor Yellow
  exit 2
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Downloading $Repo -> $OutDir"
& $Hf download $Repo --local-dir $OutDir
Write-Host "Done. Test with:"
Write-Host "  cd `"C:\Users\Isaac Sherer\Projects\colibri-lowspec\c`""
Write-Host "  python coli doctor --model $OutDir --policy lowspec"
Write-Host "  python coli chat   --model $OutDir --policy lowspec"
