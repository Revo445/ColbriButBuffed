# Ollama on your PC (no Colibri required)

## Recommended model

**`huihui_ai/qwen3-abliterated:30b-a3b`** (abliterated Qwen3-30B-A3B)

| | |
|--|--|
| Download | ~**19 GB** (Q4) |
| RAM to run | ~**21–24 GB** (fits your ~32 GB box) |
| Active params | ~**3B** / token → usable on **CPU / Radeon** |
| Abliterated | Yes (huihui-ai) |

Stock (censored) alternative: `qwen3:30b`.

### Setup / download

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec"
git pull origin cursor/cloud-agent-1785957627164-dbjnb

powershell -ExecutionPolicy Bypass -File .\scripts\Setup-Ollama-Qwen3-Abliterated.ps1
```

Or manually:

```powershell
ollama pull huihui_ai/qwen3-abliterated:30b-a3b
ollama run huihui_ai/qwen3-abliterated:30b-a3b
```

Do **not** use `:30b-a3b-q8_0` on this PC — Q8 needs ~32+ GB and will thrash.

## Use with ColbriChat

1. Ollama running in the tray.
2. API endpoint **`http://127.0.0.1:11434/v1`**
3. Probe → pick the abliterated model → chat.

## Use with ColbriChat

1. Leave Ollama running (tray / `ollama serve`).
2. In ColbriChat, set API to **`http://127.0.0.1:11434/v1`**
3. Probe → pick `qwen3:30b` → chat.

No `coli serve`, no 350 GB model.

## What we are not doing

- Not redownloading GLM-5.2
- Not using DeepSeek-V4-Flash GGUF (87–165 GB; still heavy; not needed for this path)
- Not Colibri — Ollama only
