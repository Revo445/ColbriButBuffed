# ColbriButBuffed desktop (blue steel)

Tauri v2 shell for the shared React UI in `../web`, branded for
[ColbriButBuffed](https://github.com/Revo445/ColbriButBuffed).

Theme: cool **blue / steel-gray** (`#5b8def` on `#0c1016`). The app connects to a
local `coli serve` / OpenAI-compatible endpoint — it does **not** bundle the
372 GB model or the C engine.

## Build the Windows `.exe` (one-time toolchain)

1. [Rust](https://rustup.rs/) (already used for this fork)
2. [Visual Studio 2022 Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with the **Desktop development with C++** workload (`link.exe`)
3. Node.js + npm
4. WebView2 (usually already on Windows 11)

```powershell
# From repo root
cd web
npm ci
cd ..\desktop

# Generate icons from the blue/gray source (optional after changing art)
npm exec -- tauri icon src-tauri/icons/icon-source.png

# Build installer + exe
npm exec -- tauri build
```

Outputs land under:

```
desktop\src-tauri\target\release\ColbriButBuffed.exe
desktop\src-tauri\target\release\bundle\nsis\*.exe
desktop\src-tauri\target\release\bundle\msi\*.msi
```

## Run against your local engine

In one terminal (engine + API):

```powershell
cd c
python coli serve --model D:\glm52_i4 --policy lowspec
```

Then launch `ColbriButBuffed.exe` and set the API endpoint to the serve URL
(typically `http://127.0.0.1:8000/v1` — check the serve banner).

## Dev mode

```powershell
cd desktop
npm exec -- tauri dev
```
