# Colibri + abliterated: what actually exists

## Short answer

For **ColbriButBuffed / `coli`**, the only public **abliterated** frontier MoE container is still:

**[leonid-k/GLM-5.2-abliterated-int4-colibri](https://huggingface.co/leonid-k/GLM-5.2-abliterated-int4-colibri)** (~350 GB)

There is **no** smaller Colibri-format abliterated DeepSeek / Qwen / “Flash” build on Hugging Face today.

| Candidate | Size | Abliterated? | Runs in coli? |
|-----------|------|--------------|---------------|
| `leonid-k/GLM-5.2-abliterated-int4-colibri` | ~350 GB | Yes | **Yes** |
| `annelo/GLM-5.2-FP8-Uncensored-Colibri-Int4` | ~370 GB | Uncensored (not the same recipe); older per-row int4 | Yes, but upstream prefers **gs64** |
| Huihui DeepSeek GGUF (MXFP4 ~145 GB) | ~145 GB | Yes | **No** (GGUF → llama.cpp/ds4) |
| MiMo / Hy3 Colibri int4 | ~150 GB | No | Needs matching engine build; not abliterated |
| ComfyUI Heretic NVFP4 | ~16 GB | N/A (video encoder) | **No** |

So: **abliterated + Colibri + worth using on a 32 GB box** ⇒ disk-streamed **GLM-5.2 abliterated**. It is larger than RAM on purpose; that is how Colibri works.

## Cleanup + keep / restore GLM abliterated

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec"
git pull origin cursor/cloud-agent-1785957627164-dbjnb

# Deletes DeepSeek GGUF / stock GLM leftovers; keeps or re-downloads C:\glm52_ablit
powershell -ExecutionPolicy Bypass -File .\scripts\Keep-Colibri-GlmAbliterated.ps1

# Optional: also wipe ComfyUI MiniMax model folders
powershell -ExecutionPolicy Bypass -File .\scripts\Keep-Colibri-GlmAbliterated.ps1 -RemoveComfyModels
```

Then:

```powershell
cd c
python coli chat --model C:\glm52_ablit --policy lowspec
```

Or `desktop\dist\StartColbriButBuffed.exe`.
