#!/usr/bin/env python3
"""Unit tests for tools/cluster_lb.py (stdlib unittest)."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import cluster_lb  # noqa: E402


class _FakeServe(BaseHTTPRequestHandler):
    active = 0
    capacity = 1

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({
                "status": "ok",
                "scheduler": {"active": self.active, "capacity": self.capacity, "queued": 0},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/v1/"):
            body = b'{"ok":true,"backend":"a"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)


def _serve(handler_cls, port_holder):
    httpd = HTTPServer(("127.0.0.1", 0), handler_cls)
    port_holder.append(httpd.server_address[1])
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


class ClusterLbTest(unittest.TestCase):
    def test_parse_backends(self):
        self.assertEqual(
            cluster_lb._parse_backends("http://a:1, b:2, ,https://c:3"),
            ["http://a:1", "http://b:2", "https://c:3"],
        )

    def test_pick_prefers_free_capacity(self):
        ports = []

        class Busy(_FakeServe):
            active = 1
            capacity = 1

        class Free(_FakeServe):
            active = 0
            capacity = 1

        busy = _serve(Busy, ports)
        free = _serve(Free, ports)
        try:
            pool = cluster_lb.BackendPool([
                f"http://127.0.0.1:{ports[0]}",
                f"http://127.0.0.1:{ports[1]}",
            ], health_ttl=0)
            choice = pool.pick()
            self.assertEqual(choice, f"http://127.0.0.1:{ports[1]}")
        finally:
            busy.shutdown()
            free.shutdown()


if __name__ == "__main__":
    unittest.main()
