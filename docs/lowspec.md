# Lowspec guide — GLM-5.2 on 25–64 GB RAM

**ColbriButBuffed** is a [Colibrì](https://github.com/JustVugg/colibri) fork aimed at
PCs that cannot keep the expert set resident. The engine still streams ~370 GB of
int4 experts from NVMe; this guide documents the `--policy lowspec` defaults that
keep that path stable on tight hosts.

## Honest expectations

| Host | What to expect |
|------|----------------|
| ~25 GB RAM, cold cache | Often **0.05–0.1 tok/s** (or slower). Correct, not interactive. |
| ~32 GB RAM, warming `.coli_usage` | Still disk-bound; hit rate rises over turns; often still **&lt;1 tok/s**. |
| ~64 GB RAM, warm pins | More LRU + pin room; still far from full residency (~370 GB experts). |
| Fast NVMe | Token speed ≈ disk bandwidth × expert hit rate. HDD / network mounts are a non-starter. |

Placement never changes tokens or precision — only speed.

## What you need

| | Minimum | Recommended |
|---|---|---|
| **RAM** | ~25 GB usable | 32–64 GB |
| **Disk** | ~380 GB free for the int4 model | Local NVMe (not USB / network) |
| **OS** | Windows 10/11, Linux, or macOS | Windows is first-class for this fork |
| **GPU** | Optional | Lowspec defaults to **CPU-first** so VRAM host copies do not steal RAM |

Use the **gs64** GLM-5.2 container with **int8 MTP heads** from the upstream README
(int4 MTP heads silently destroy draft acceptance). Lowspec turns **MTP off**
(`DRAFT=0`) because speculation widens the expert union on disk-bound hosts.

## Windows PowerShell quick path

1. Install [Python 3](https://www.python.org/downloads/) and build tools
   ([docs/windows.md](windows.md) — MinGW + `sh.exe`, or a release zip).
2. Download the model to a fast local drive (hours; resumable):

```powershell
python -m pip install -U "huggingface_hub[hf_transfer]"
$env:HF_HUB_ENABLE_HF_TRANSFER = "1"
hf download mastouri/GLM-5.2-colibri-int4-g64-with-int8-mtp --local-dir D:\glm52_i4
```

3. From this repo’s `c\` directory:

```powershell
python coli doctor --model D:\glm52_i4 --policy lowspec
python coli plan   --model D:\glm52_i4 --policy lowspec
python coli chat   --model D:\glm52_i4 --policy lowspec
```

Optional: measure whether `DIRECT=1` helps on *your* drive:

```powershell
make iobench.exe
.\iobench.exe D:\glm52_i4
# If buffered beats DIRECT, run with DIRECT=0
$env:DIRECT = "0"
python coli chat --model D:\glm52_i4 --policy lowspec
```

## What `--policy lowspec` sets

All of these use `setdefault` — an explicit env var or CLI flag still wins.

| Knob | Lowspec default | Why |
|------|-----------------|-----|
| `PIPE` | `1` | Overlap expert reads with compute |
| `DIRECT` | `1` | Unbuffered reads (drive-dependent; measure) |
| `PILOT_REAL` | `1` | Real cross-layer prefetch (needed on Windows) |
| `DRAFT` | `0` | MTP hurts when hit rate is low |
| `CAP_RAISE` | `0` | Avoid thrashing under memory pressure |
| `PIN_GB` | `2` or `4` (or `all` if fully resident) | Default `10` starves the LRU on ~32 GB |
| `REPIN` | `32` | Modest live re-pin from usage history |
| `CTX` | `2048` | Smaller KV reserve than 4096 on tight RAM |
| CUDA | off unless `--gpu` / `--vram` | Keep RAM for the expert cache |

Also: `COLI_POLICY=lowspec` is exported so logs and tools see the same policy.

## After the first turns

The engine writes `.coli_usage` next to the model. Later sessions **AUTOPIN** hot
experts from that history — the main warm-path win on low-spec boxes. Keep the
model directory writable.

## Related docs

- Upstream quick start: [quickstart.md](quickstart.md)
- Windows deep dive: [windows.md](windows.md)
- Env reference: [ENVIRONMENT.md](ENVIRONMENT.md)
- Upstream project: https://github.com/JustVugg/colibri
- This fork: https://github.com/Revo445/ColbriButBuffed
