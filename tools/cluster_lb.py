#!/usr/bin/env python3
"""ColbriButBuffed — OpenAI-compatible load balancer for multiple coli serve nodes.

Does NOT shard a single decode across machines. Each backend is a full coli serve
with a local model copy; this process fans out concurrent HTTP clients.

  COLI_BACKENDS=http://10.0.0.11:8000,http://10.0.0.12:8000 \\
    python3 tools/cluster_lb.py --host 0.0.0.0 --port 8080

Stdlib only. Streaming responses are forwarded as raw chunks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


def _parse_backends(raw: str) -> list[str]:
    out = []
    for part in (raw or "").split(","):
        part = part.strip().rstrip("/")
        if not part:
            continue
        if not part.startswith("http://") and not part.startswith("https://"):
            part = "http://" + part
        out.append(part)
    return out


class BackendPool:
    def __init__(self, backends: list[str], health_ttl: float = 2.0):
        if not backends:
            raise SystemExit("no backends: set COLI_BACKENDS or pass --backend")
        self.backends = list(backends)
        self.health_ttl = health_ttl
        self._lock = threading.Lock()
        self._rr = 0
        self._cache: dict[str, tuple[float, dict | None]] = {}

    def health(self, base: str) -> dict | None:
        now = time.time()
        with self._lock:
            cached = self._cache.get(base)
            if cached and now - cached[0] < self.health_ttl:
                return cached[1]
        try:
            req = urllib.request.Request(base + "/health", method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            data = None
        with self._lock:
            self._cache[base] = (now, data)
        return data

    def pick(self) -> str | None:
        """Prefer reachable backends with the most free scheduler capacity."""
        scored: list[tuple[tuple, str]] = []
        for base in self.backends:
            h = self.health(base)
            if h is None:
                continue
            sch = h.get("scheduler") or {}
            capacity = int(sch.get("capacity") or 1)
            active = int(sch.get("active") or 0)
            queued = int(sch.get("queued") or 0)
            free = max(0, capacity - active)
            # Higher free first; lower queue next; stable by address.
            scored.append(((-free, queued, active), base))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0])
        best_key = scored[0][0]
        candidates = [b for key, b in scored if key == best_key]
        with self._lock:
            choice = candidates[self._rr % len(candidates)]
            self._rr += 1
        return choice

    def snapshot(self) -> list[dict]:
        rows = []
        for base in self.backends:
            h = self.health(base)
            rows.append({"backend": base, "ok": h is not None, "health": h})
        return rows


class Handler(BaseHTTPRequestHandler):
    pool: BackendPool
    api_key: str | None = None

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _auth_ok(self) -> bool:
        if not self.api_key:
            return True
        header = self.headers.get("Authorization", "")
        if header == f"Bearer {self.api_key}":
            return True
        return self.headers.get("x-api-key") == self.api_key

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def do_GET(self):
        if not self._auth_ok() and urlsplit(self.path).path not in ("/health", "/lb/health"):
            self.send_error(401, "unauthorized")
            return
        path = urlsplit(self.path).path
        if path in ("/health", "/lb/health"):
            rows = self.pool.snapshot()
            ok = any(r["ok"] for r in rows)
            body = json.dumps({
                "status": "ok" if ok else "degraded",
                "backends": rows,
                "role": "colbri-cluster-lb",
            }).encode("utf-8")
            self.send_response(200 if ok else 503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._proxy("GET", b"")

    def do_POST(self):
        if not self._auth_ok():
            self.send_error(401, "unauthorized")
            return
        self._proxy("POST", self._read_body())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, x-api-key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def _proxy(self, method: str, body: bytes):
        path = self.path
        if path.startswith("/lb/"):
            self.send_error(404, "not found")
            return
        backend = self.pool.pick()
        if backend is None:
            msg = b'{"error":{"message":"no healthy coli serve backends","type":"cluster_unavailable"}}'
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return

        url = backend + path
        headers = {}
        for key in ("Content-Type", "Accept", "Authorization", "x-api-key"):
            if key in self.headers:
                headers[key] = self.headers[key]
        req = urllib.request.Request(url, data=body if method != "GET" else None,
                                     headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                self.send_response(resp.status)
                ctype = resp.headers.get("Content-Type")
                if ctype:
                    self.send_header("Content-Type", ctype)
                # Streaming: do not buffer the whole body.
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            msg = json.dumps({"error": {"message": str(exc), "type": "proxy_error",
                                        "backend": backend}}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)


def main(argv=None):
    p = argparse.ArgumentParser(description="ColbriButBuffed coli serve load balancer")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--backend", action="append", default=[],
                   help="Backend base URL (repeatable). Also COLI_BACKENDS=a,b")
    p.add_argument("--api-key", default=os.environ.get("COLI_LB_API_KEY"))
    args = p.parse_args(argv)

    backends = list(args.backend) + _parse_backends(os.environ.get("COLI_BACKENDS", ""))
    # de-dupe, preserve order
    seen = set()
    ordered = []
    for b in backends:
        b = b.rstrip("/")
        if b not in seen:
            seen.add(b)
            ordered.append(b)

    pool = BackendPool(ordered)
    Handler.pool = pool
    Handler.api_key = args.api_key
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"colbri cluster LB on http://{args.host}:{args.port}", file=sys.stderr)
    for b in ordered:
        print(f"  backend {b}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
