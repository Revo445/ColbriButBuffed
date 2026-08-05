#!/usr/bin/env python3
"""ColbriButBuffed — simple local chat client for coli serve."""

from __future__ import annotations

import json
import queue
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
from tkinter import messagebox, scrolledtext, ttk

DEFAULT_BASE = "http://127.0.0.1:8000/v1"
DEFAULT_MAX_TOKENS = 256
POLL_MS = 80


class ChatApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ColbriButBuffed Chat")
        self.geometry("920x680")
        self.minsize(720, 520)
        self.configure(bg="#0c1016")

        self.base_url = tk.StringVar(value=DEFAULT_BASE)
        self.model = tk.StringVar(value="")
        self.status = tk.StringVar(value="Not connected — click Connect")
        self.max_tokens = tk.IntVar(value=DEFAULT_MAX_TOKENS)

        self.history: list[dict[str, str]] = []
        self.busy = False
        self.abort = threading.Event()
        self.ui_q: queue.Queue = queue.Queue()
        self._gen_thread: threading.Thread | None = None

        self._build()
        self.after(POLL_MS, self._drain_ui)
        self.after(400, self.connect)

    def _build(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#0c1016")
        style.configure("TLabel", background="#0c1016", foreground="#d7e0ef")
        style.configure("TButton", padding=6)
        style.configure("Status.TLabel", foreground="#8fb4ff", font=("Segoe UI", 10, "bold"))

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="API").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.base_url, width=42).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="Connect", command=self.connect).grid(row=0, column=2, padx=2)
        ttk.Button(top, text="Stop", command=self.stop_generation).grid(row=0, column=3, padx=2)

        ttk.Label(top, text="Model").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.model_box = ttk.Combobox(top, textvariable=self.model, state="readonly", width=40)
        self.model_box.grid(row=1, column=1, sticky="ew", padx=6, pady=(8, 0))
        ttk.Label(top, text="Max tokens").grid(row=1, column=2, sticky="e", pady=(8, 0))
        ttk.Spinbox(top, from_=32, to=2048, increment=32, textvariable=self.max_tokens, width=8).grid(
            row=1, column=3, sticky="w", pady=(8, 0)
        )
        top.columnconfigure(1, weight=1)

        ttk.Label(self, textvariable=self.status, style="Status.TLabel", padding=(12, 4)).pack(fill="x")

        self.log = scrolledtext.ScrolledText(
            self,
            wrap="word",
            font=("Cascadia Mono", 11),
            bg="#121826",
            fg="#e8eef8",
            insertbackground="#e8eef8",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.log.tag_configure("user", foreground="#8fb4ff")
        self.log.tag_configure("assistant", foreground="#d7e0ef")
        self.log.tag_configure("system", foreground="#9aa8bc")
        self.log.tag_configure("error", foreground="#ff8f8f")
        self.log.configure(state="disabled")

        bottom = ttk.Frame(self, padding=12)
        bottom.pack(fill="x")
        self.input = scrolledtext.ScrolledText(
            bottom,
            height=4,
            wrap="word",
            font=("Segoe UI", 11),
            bg="#1a2230",
            fg="#e8eef8",
            insertbackground="#e8eef8",
            relief="flat",
        )
        self.input.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.input.bind("<Control-Return>", lambda _e: self.send())
        ttk.Button(bottom, text="Send\n(Ctrl+Enter)", command=self.send).pack(side="right", fill="y")

        self._append("system", "ColbriButBuffed simple chat\nTalks to coli serve at the API above.\n")

    def _append(self, tag: str, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text, tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text: str) -> None:
        self.status.set(text)

    def _drain_ui(self) -> None:
        try:
            while True:
                kind, payload = self.ui_q.get_nowait()
                if kind == "status":
                    self._set_status(payload)
                elif kind == "append":
                    tag, text = payload
                    self._append(tag, text)
                elif kind == "done":
                    self.busy = False
                    self._set_status(payload)
                elif kind == "models":
                    models = payload
                    self.model_box["values"] = models
                    if models and self.model.get() not in models:
                        self.model.set(models[0])
        except queue.Empty:
            pass
        self.after(POLL_MS, self._drain_ui)

    def _endpoint(self, path: str) -> str:
        """path is '/models', '/chat/completions', or '/health'."""
        base = self.base_url.get().strip().rstrip("/")
        if not base.endswith("/v1"):
            base = base + "/v1"
        root = base[:-3]  # strip /v1
        if path == "/health":
            return root + "/health"
        return base + path

    def connect(self) -> None:
        def work() -> None:
            try:
                with urllib.request.urlopen(self._endpoint("/models"), timeout=5) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                models = [m["id"] for m in payload.get("data", [])]
                health_note = ""
                try:
                    with urllib.request.urlopen(self._endpoint("/health"), timeout=5) as resp:
                        health = json.loads(resp.read().decode("utf-8"))
                    sch = health.get("scheduler") or {}
                    hw = health.get("hwinfo") or {}
                    health_note = (
                        f" · active {sch.get('active', '?')}/{sch.get('capacity', '?')}"
                        f" · RAM free {hw.get('ram_avail_gb', '?')} GB"
                    )
                except Exception:
                    pass
                self.ui_q.put(("models", models))
                self.ui_q.put(("status", f"Connected · {', '.join(models) or 'no models'}{health_note}"))
                self.ui_q.put(("append", ("system", f"[connected] {models}\n")))
            except Exception as exc:
                self.ui_q.put(("status", f"Not connected — {exc}"))
                self.ui_q.put(
                    (
                        "append",
                        (
                            "error",
                            "Could not reach server. Start it first:\n"
                            "  cd c\n"
                            "  python coli serve --model C:\\glm52_ablit --policy lowspec\n\n",
                        ),
                    )
                )

        threading.Thread(target=work, daemon=True).start()

    def stop_generation(self) -> None:
        self.abort.set()
        self._set_status("Stopping… (server may finish the current token)")

    def send(self) -> None:
        if self.busy:
            messagebox.showinfo("Busy", "Wait for the current reply, or click Stop.")
            return
        text = self.input.get("1.0", "end").strip()
        if not text:
            return
        if not self.model.get():
            messagebox.showwarning("No model", "Connect first so a model id is available.")
            return

        self.input.delete("1.0", "end")
        self.history.append({"role": "user", "content": text})
        self._append("user", f"\nYou\n{text}\n")
        self._append("assistant", "\nColbri\n")
        self.busy = True
        self.abort.clear()
        self._set_status("Sending… (first tokens can take minutes on lowspec/disk)")

        messages = list(self.history)
        model = self.model.get()
        max_tokens = int(self.max_tokens.get())
        url = self._endpoint("/chat/completions")

        def work() -> None:
            started = time.time()
            tokens = 0
            reply_parts: list[str] = []
            body = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    buf = b""
                    done = False
                    self.ui_q.put(("status", "Waiting for first token (disk-bound can take several minutes)…"))
                    while not self.abort.is_set() and not done:
                        chunk = resp.read(256)
                        if not chunk:
                            break
                        buf += chunk
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            line = line.strip()
                            if not line or line.startswith(b":"):
                                continue
                            if not line.startswith(b"data:"):
                                continue
                            payload = line[5:].strip()
                            if payload == b"[DONE]":
                                done = True
                                break
                            try:
                                obj = json.loads(payload.decode("utf-8"))
                            except json.JSONDecodeError:
                                continue
                            delta = ((obj.get("choices") or [{}])[0].get("delta") or {})
                            piece = delta.get("content") or delta.get("reasoning_content") or ""
                            if piece:
                                tokens += 1
                                reply_parts.append(piece)
                                elapsed = max(time.time() - started, 0.001)
                                self.ui_q.put(("append", ("assistant", piece)))
                                self.ui_q.put(
                                    (
                                        "status",
                                        f"Streaming · ~{tokens} chunks · {elapsed:.0f}s · {tokens / elapsed:.2f} chunk/s",
                                    )
                                )
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                self.ui_q.put(("append", ("error", f"\n[HTTP {exc.code}] {detail}\n")))
                self.ui_q.put(("done", f"Error HTTP {exc.code}"))
                return
            except Exception as exc:
                self.ui_q.put(("append", ("error", f"\n[error] {exc}\n")))
                self.ui_q.put(("done", f"Error: {exc}"))
                return

            reply = "".join(reply_parts).strip()
            if reply:
                self.history.append({"role": "assistant", "content": reply})
            elif self.abort.is_set():
                self.ui_q.put(("append", ("system", "\n[stopped]\n")))
            else:
                self.ui_q.put(
                    (
                        "append",
                        (
                            "system",
                            "\n[no tokens yet — server may still be loading experts from disk; try Connect then send again]\n",
                        ),
                    )
                )
            elapsed = max(time.time() - started, 0.001)
            self.ui_q.put(("append", ("system", "\n")))
            self.ui_q.put(("done", f"Done · {tokens} chunks in {elapsed:.0f}s"))

        self._gen_thread = threading.Thread(target=work, daemon=True)
        self._gen_thread.start()


def main() -> None:
    app = ChatApp()
    app.mainloop()


if __name__ == "__main__":
    main()
