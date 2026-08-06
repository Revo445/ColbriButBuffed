# ColbriButBuffed Windows chat + starter

## Where the `.exe` files live (on your PC)

After a local Windows build they are under:

| File | What it does |
|------|----------------|
| `desktop\dist\ColbriChat.exe` | Chat UI only — **does not** start the engine |
| `desktop\dist\ColbriButBuffed.exe` | Full Tauri UI — also needs `coli serve` already running |
| `desktop\dist\StartColbriButBuffed.exe` | **One-click**: start `coli serve --policy lowspec` + open chat |

If `StartColbriButBuffed.exe` is missing, double-click:

`tools\simple_chat\Start ColbriButBuffed.bat`

(default model path: `C:\glm52_ablit`)

## Build the starter `.exe` (Windows)

```powershell
cd "C:\Users\Isaac Sherer\Projects\colibri-lowspec\tools\simple_chat"
python -m pip install pyinstaller
python -m PyInstaller --noconfirm StartColbriButBuffed.spec
New-Item -ItemType Directory -Force -Path ..\..\desktop\dist | Out-Null
Copy-Item dist\StartColbriButBuffed.exe ..\..\desktop\dist\ -Force
```

Then run:

```
desktop\dist\StartColbriButBuffed.exe
```
