# DeepSeek-V4-Flash abliterated (GGUF) — not Colibri

ColbriButBuffed / `coli` **cannot** load GGUF. After switching off GLM-5.2 abliterated,
run this model with **llama.cpp** or **antirez/ds4** (MXFP4: `ds4f-mxfp4` branch).

## Quant you asked for

| File | Approx size |
|------|-------------|
| `DeepSeek-V4-Flash-Q4-mxfp4-0731.gguf` | **~145 GB** |

Repo: [huihui-ai/Huihui-DeepSeek-V4-Flash-0731-abliterated-GGUF](https://huggingface.co/huihui-ai/Huihui-DeepSeek-V4-Flash-0731-abliterated-GGUF)

Smaller than GLM Colibri (~350 GB), still large. On ~32 GB RAM expect heavy mmap / disk I/O;
13B active MoE experts help, but it will not feel “small.”

## One-shot: delete GLM abliterated + download MXFP4

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec"
git pull origin cursor/cloud-agent-1785957627164-dbjnb

powershell -ExecutionPolicy Bypass -File .\scripts\Switch-To-DeepSeek-MXFP4.ps1
```

Defaults:

- Deletes `C:\glm52_ablit`
- Downloads to `C:\deepseek_v4_flash\DeepSeek-V4-Flash-Q4-mxfp4-0731.gguf`

Options:

```powershell
# Keep GLM weights
.\scripts\Switch-To-DeepSeek-MXFP4.ps1 -KeepGlm

# Other drive
.\scripts\Switch-To-DeepSeek-MXFP4.ps1 -OutDir D:\models\deepseek
```

## Run (after download)

**llama.cpp** (latest build):

```powershell
llama-server -m "C:\deepseek_v4_flash\DeepSeek-V4-Flash-Q4-mxfp4-0731.gguf" `
  -c 8192 --host 127.0.0.1 --port 8080 --jinja
```

Then point ColbriChat at `http://127.0.0.1:8080/v1` (not Colibri’s port 8000 engine).

**ds4** (NVIDIA; MXFP4 branch): https://github.com/antirez/ds4/tree/ds4f-mxfp4
