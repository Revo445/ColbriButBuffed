# ComfyUI + MiniMax-H3 with Heretic NVFP4 encoder

This is **not** Colibri. The Hugging Face file
[`sakamakismile/Qwen3-VL-32B-Heretic-MiniMax-H3-NVFP4`](https://huggingface.co/sakamakismile/Qwen3-VL-32B-Heretic-MiniMax-H3-NVFP4)
is a **ComfyUI text encoder** for MiniMax-H3 video (CLIPLoader type `minimax`).

## Hardware reality check

| Piece | Note |
|-------|------|
| **NVIDIA GPU** | Strongly recommended. Official MiniMax-H3 targets CUDA; NVFP4 is a Tensor-Core layout. |
| **AMD iGPU (e.g. Radeon 880M)** | May fail or be extremely slow; do not expect the measured ~16 GB Blackwell path. |
| **RAM** | Plan on **≥32 GB system RAM** (upstream measured ~36 GB process RSS with offload). |
| **Disk** | ~**45 GB** for Heretic encoder + pruned diffusion + VAEs (T2V/I2V set). |

## What the installer puts where

Default root: `C:\ComfyUI` (override with `-ComfyRoot`).

```
ComfyUI/
├── models/
│   ├── text_encoders/
│   │   └── qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors   ← Heretic (this HF repo)
│   ├── diffusion_models/
│   │   └── minimax_h3_fl2va_pruned_int8_convrot.safetensors   ← T2V / I2V
│   └── vae/
│       ├── minimax_h3_video_vae_fp16.safetensors
│       └── minimax_h3_audio_vae_fp32.safetensors
```

Optional R2V diffusion (extra ~21 GB):
`minimax_h3_ref2va_pruned_int8_convrot.safetensors`

## One-shot Windows setup

From an elevated-enough PowerShell (normal user is fine):

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec"
git pull origin cursor/cloud-agent-1785957627164-dbjnb

# Install ComfyUI + download Heretic encoder + MiniMax pruned stack (~45 GB)
powershell -ExecutionPolicy Bypass -File .\scripts\comfyui\Setup-MiniMaxH3.ps1

# Later launches:
.\scripts\comfyui\Start-ComfyUI.bat
```

Flags:

```powershell
# Custom install location
.\scripts\comfyui\Setup-MiniMaxH3.ps1 -ComfyRoot D:\ComfyUI

# Also fetch R2V diffusion weights
.\scripts\comfyui\Setup-MiniMaxH3.ps1 -IncludeR2V

# Skip clone if ComfyUI already exists; only fetch models
.\scripts\comfyui\Setup-MiniMaxH3.ps1 -ModelsOnly
```

## In ComfyUI after install

1. Update/use **ComfyUI ≥ 0.30.0**.
2. **Template Library → Video → MiniMax H3 T2V** (or I2V / R2V).
3. On **CLIPLoader**:
   - **clip_name**: `qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors`
   - **type**: `minimax`
4. Leave diffusion + VAEs on the pruned Comfy-Org files the script downloaded.
5. Queue a short low-megapixel test first.

Official docs: https://docs.comfy.org/tutorials/video/minimax/minimax-h3  
Comfy-Org weights: https://huggingface.co/Comfy-Org/MiniMax-H3  
Heretic encoder: https://huggingface.co/sakamakismile/Qwen3-VL-32B-Heretic-MiniMax-H3-NVFP4

## Relation to ColbriButBuffed

Colibri/`coli serve` cannot load this file. Keep GLM chat on ColbriButBuffed; use ComfyUI for MiniMax-H3 video.
