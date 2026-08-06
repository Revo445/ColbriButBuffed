# Abliterated GLM-5.2 on ColbriButBuffed

Colibri **cannot** load Huihui’s GGUF release
(`huihui-ai/Huihui-GLM-5.2-abliterated-GGUF`). It only runs **Colibri int4
safetensors** containers.

## Recommended Colibri container

Community Colibri-format abliterated weights:

**https://huggingface.co/leonid-k/GLM-5.2-abliterated-int4-colibri**

Same layout as stock Colibri GLM-5.2 (`out-*.safetensors` + `config.json` +
`tokenizer.json`). No MTP head in that repo — fine with `--policy lowspec`
(which already sets `DRAFT=0`).

## Disk

Expect ~**400 GB**. On a machine that already has `C:\glm52_i4` (~400 GB) and
only ~200 GB free, **free space first** (move/delete the stock model, or use
another drive).

## Download (PowerShell)

```powershell
# Optional: free the stock model if you need the space
# Rename-Item C:\glm52_i4 C:\glm52_i4_stock_backup   # or Remove-Item -Recurse

New-Item -ItemType Directory -Force -Path C:\glm52_ablit | Out-Null

& "$env:LOCALAPPDATA\Python\pythoncore-3.14-64\Scripts\hf.exe" download `
  leonid-k/GLM-5.2-abliterated-int4-colibri `
  --local-dir C:\glm52_ablit
```

Resume by re-running the same `hf download` line.

## Run

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec\c"

python coli doctor --model C:\glm52_ablit --policy lowspec
python coli chat   --model C:\glm52_ablit --policy lowspec
```

Or serve + desktop app:

```powershell
python coli serve --model C:\glm52_ablit --policy lowspec
# then open desktop\dist\ColbriButBuffed.exe → probe http://127.0.0.1:8000/v1
```

## Notes

- Abliteration reduces refusals; it does not change Colibri’s streaming engine.
- Quality / safety trade-offs are on you — this is an uncensored community build.
- If you later want a from-scratch convert of your own FP8 abliterated source:
  `python coli convert --model C:\out --repo <your-fp8-repo>` (needs torch + lots of time).
