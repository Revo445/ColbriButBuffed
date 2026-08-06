# Ollama on your PC (no Colibri required)

## Recommended model

**`qwen3:30b`** (Qwen3-30B-A3B MoE)

| | |
|--|--|
| Download | ~**19 GB** |
| RAM to run | ~**21–24 GB** (fits your ~32 GB box) |
| Active params | ~**3B** / token → much snappier on **CPU / Radeon** than dense 32B or GLM streaming |
| Strength | Coding, reasoning, general chat — strong “worth using” tier without 350 GB of experts |

Your GLM-5.2 Colibri path was correct but **disk-bound** on this machine (often &lt;1 tok/s, easy to look “broken” on long code). Ollama + Qwen3-30B-A3B is the practical replacement.

### Alternatives

| Model | When |
|-------|------|
| `qwen3:14b` (~9 GB) | More RAM headroom / faster |
| `deepseek-r1:32b` (~20 GB) | Prefer long “thinking” traces |
| `qwen2.5-coder:32b` (~20 GB) | Coding-focused dense 32B (slower than 30B-A3B on CPU) |

Abliterated 32B distills exist on HF, but for a **reliable first Ollama install** use the official `qwen3:30b` tag.

## Setup

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec"
git pull origin cursor/cloud-agent-1785957627164-dbjnb

powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Ollama-Qwen3.ps1
```

Then:

```powershell
ollama run qwen3:30b
```

## Use with ColbriChat

1. Leave Ollama running (tray / `ollama serve`).
2. In ColbriChat, set API to **`http://127.0.0.1:11434/v1`**
3. Probe → pick `qwen3:30b` → chat.

No `coli serve`, no 350 GB model.

## What we are not doing

- Not redownloading GLM-5.2
- Not using DeepSeek-V4-Flash GGUF (87–165 GB; still heavy; not needed for this path)
- Not Colibri — Ollama only
