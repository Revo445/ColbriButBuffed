#!/usr/bin/env python3
"""ColbriButBuffed one-click starter for Windows.

Starts `coli serve` (lowspec) if nothing is listening on the API port, waits
until /v1/models answers, then opens ColbriChat (or the Tauri app).

Build on Windows:
  pyinstaller --noconfirm --onefile --windowed --name StartColbriButBuffed start_colbri.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

DEFAULT_MODEL = r"C:\glm52_ablit"
DEFAULT_PORT = 8000
DEFAULT_BASE = f"http://127.0.0.1:{DEFAULT_PORT}/v1"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def _looks_like_repo(path: Path) -> bool:
    return (path / "c" / "coli").is_file()


def repo_root() -> Path:
    """Find the ColbriButBuffed checkout — never use PyInstaller _MEI temp dirs."""
    env = os.environ.get("COLI_ROOT", "").strip()
    if env and _looks_like_repo(Path(env)):
        return Path(env).resolve()

    candidates: list[Path] = []
    if _is_frozen():
        # StartColbriButBuffed.exe lives in desktop/dist or tools/simple_chat/dist
        exe = Path(sys.executable).resolve()
        candidates.extend([exe.parent, exe.parent.parent, exe.parent.parent.parent])
        # desktop/dist -> repo; tools/simple_chat/dist -> repo
        if exe.parent.name == "dist":
            candidates.append(exe.parents[2])  # desktop/dist or simple_chat/dist
            candidates.append(exe.parents[3])
    else:
        here = Path(__file__).resolve()
        if here.parent.name == "simple_chat":
            candidates.append(here.parents[2])
        candidates.append(here.parent)

    candidates.append(Path.cwd())
    # Walk upward from cwd and from exe/script location
    seeds = list(candidates)
    for seed in seeds:
        cur = seed.resolve()
        for _ in range(6):
            candidates.append(cur)
            if cur.parent == cur:
                break
            cur = cur.parent

    seen: set[Path] = set()
    for path in candidates:
        try:
            path = path.resolve()
        except OSError:
            continue
        if path in seen:
            continue
        seen.add(path)
        if _looks_like_repo(path):
            return path

    # Last resort: common clone path from earlier sessions
    fallback = Path(r"C:\Users\Isaac Sherer\Projects\colibri-lowspec")
    if _looks_like_repo(fallback):
        return fallback

    # Return best guess for error messages
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_chat_exe(root: Path) -> Path | None:
    candidates = [
        root / "desktop" / "dist" / "ColbriChat.exe",
        root / "tools" / "simple_chat" / "dist" / "ColbriChat.exe",
        Path(sys.executable).resolve().parent / "ColbriChat.exe" if _is_frozen() else None,
        root / "desktop" / "dist" / "ColbriButBuffed.exe",
    ]
    for path in candidates:
        if path and path.is_file():
            return path
    return None


def port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def api_ready(base: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/models", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def which_python() -> str:
    """Real Python interpreter — never the frozen StartColbri exe itself."""
    if not _is_frozen() and sys.executable:
        return sys.executable
    for name in ("python", "python3", "py"):
        from shutil import which
        found = which(name)
        if found and Path(found).resolve() != Path(sys.executable).resolve():
            return found
    # Windows py launcher
    from shutil import which
    py = which("py")
    if py:
        return py
    return "python"


class StarterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Start ColbriButBuffed")
        self.geometry("560x320")
        self.configure(bg="#0c1016")
        self.root = repo_root()
        self.model = tk.StringVar(value=os.environ.get("COLI_MODEL", DEFAULT_MODEL))
        self.port = tk.IntVar(value=int(os.environ.get("COLI_PORT", str(DEFAULT_PORT))))
        self.status = tk.StringVar(value="Ready")
        self.serve_proc: subprocess.Popen | None = None
        self._build()
        self.after(200, self.refresh_status)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#0c1016")
        style.configure("TLabel", background="#0c1016", foreground="#d7e0ef")
        style.configure("Status.TLabel", foreground="#8fb4ff", font=("Segoe UI", 10, "bold"))

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ColbriButBuffed launcher", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Starts coli serve (lowspec) then opens the chat app.").pack(anchor="w", pady=(0, 12))

        ttk.Label(frame, text="Model directory").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.model).pack(fill="x", pady=(0, 8))

        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Port").pack(side="left")
        ttk.Spinbox(row, from_=1024, to=65535, textvariable=self.port, width=8).pack(side="left", padx=8)

        ttk.Label(frame, textvariable=self.status, style="Status.TLabel").pack(anchor="w", pady=(8, 12))

        btns = ttk.Frame(frame)
        btns.pack(fill="x")
        ttk.Button(btns, text="Start GLM-5.2", command=self.start_all).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Open chat only", command=self.open_chat).pack(side="left", padx=(0, 8))
        ttk.Button(btns, text="Stop serve", command=self.stop_serve).pack(side="left")

        ttk.Label(
            frame,
            text=f"Repo: {self.root}\nChat exe looked for under desktop\\dist\\",
            foreground="#9aa8bc",
        ).pack(anchor="w", pady=(16, 0))

    def refresh_status(self) -> None:
        port = int(self.port.get())
        base = f"http://127.0.0.1:{port}/v1"
        if api_ready(base):
            self.status.set(f"Engine reachable on {base}")
        elif port_open("127.0.0.1", port):
            self.status.set(f"Port {port} open — waiting for model load…")
        else:
            self.status.set("Engine not running")
        self.after(1500, self.refresh_status)

    def start_all(self) -> None:
        threading.Thread(target=self._start_worker, daemon=True).start()

    def _start_worker(self) -> None:
        model = Path(self.model.get().strip())
        port = int(self.port.get())
        base = f"http://127.0.0.1:{port}/v1"
        coli = self.root / "c" / "coli"
        if not model.is_dir():
            self.status.set(f"Model missing: {model}")
            messagebox.showerror("Model not found", f"No model directory at:\n{model}")
            return
        if not coli.is_file():
            self.status.set("coli launcher missing")
            messagebox.showerror("Missing coli", f"Cannot find:\n{coli}")
            return

        if not api_ready(base):
            self.status.set("Starting coli serve (first load can take many minutes)…")
            creation = 0
            if sys.platform == "win32":
                creation = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
            log_dir = self.root / "c"
            stdout = open(log_dir / "serve_stdout.log", "a", encoding="utf-8")
            stderr = open(log_dir / "serve_stderr.log", "a", encoding="utf-8")
            cmd = [
                which_python(),
                str(coli),
                "serve",
                "--model",
                str(model),
                "--policy",
                "lowspec",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ]
            try:
                self.serve_proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.root / "c"),
                    stdout=stdout,
                    stderr=stderr,
                    creationflags=creation,
                )
            except Exception as exc:
                self.status.set(f"Failed to start serve: {exc}")
                messagebox.showerror("Start failed", str(exc))
                return

            deadline = time.time() + 3600  # model load can be very slow
            while time.time() < deadline:
                if self.serve_proc.poll() is not None:
                    self.status.set(f"serve exited early (code {self.serve_proc.returncode}) — see c\\serve_stderr.log")
                    messagebox.showerror(
                        "Serve exited",
                        "coli serve stopped before becoming ready.\nCheck c\\serve_stderr.log",
                    )
                    return
                if api_ready(base, timeout=2.0):
                    break
                self.status.set("Loading model / waiting for API…")
                time.sleep(2)
            else:
                self.status.set("Timed out waiting for API")
                messagebox.showwarning("Timeout", "Server did not become ready in time. It may still be loading.")
                return

        self.status.set("Engine ready — opening chat")
        self.open_chat()

    def open_chat(self) -> None:
        exe = find_chat_exe(self.root)
        if exe:
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
            self.status.set(f"Opened {exe.name}")
            return
        chat_py = self.root / "tools" / "simple_chat" / "colbri_chat.py"
        if chat_py.is_file():
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen([which_python(), str(chat_py)], **kwargs)
            self.status.set("Opened ColbriChat (python)")
            return
        messagebox.showerror(
            "Chat app missing",
            "Could not find ColbriChat.exe under desktop\\dist\\.\n"
            "Build it with tools\\simple_chat\\ColbriChat.spec or run colbri_chat.py",
        )

    def stop_serve(self) -> None:
        coli = self.root / "c" / "coli"
        port = int(self.port.get())
        try:
            subprocess.run(
                [which_python(), str(coli), "stop", "--port", str(port)],
                cwd=str(self.root / "c"),
                timeout=60,
            )
            self.status.set("Stop requested")
        except Exception as exc:
            self.status.set(f"Stop failed: {exc}")
        if self.serve_proc and self.serve_proc.poll() is None:
            self.serve_proc.terminate()


def main() -> None:
    app = StarterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
