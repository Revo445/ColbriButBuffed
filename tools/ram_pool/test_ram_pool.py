#!/usr/bin/env python3
"""Tests for tools/ram_pool."""

from __future__ import annotations

import json
import struct
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler  # noqa: F401 — keep import style consistent
from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ram_pool import index_model, list_expert_ids, read_expert, route_worker  # noqa: E402
import ram_pool.worker as worker_mod  # noqa: E402


def write_safetensors(path: Path, tensors: dict[str, bytes]):
    header = {}
    offset = 0
    payload = b""
    for name, data in tensors.items():
        header[name] = {"dtype": "U8", "shape": [len(data)], "data_offsets": [offset, offset + len(data)]}
        payload += data
        offset += len(data)
    raw = json.dumps(header).encode("utf-8")
    path.write_bytes(struct.pack("<Q", len(raw)) + raw + payload)


class RamPoolTest(unittest.TestCase):
    def test_route_stable(self):
        self.assertEqual(route_worker(0, 0, 3), route_worker(0, 0, 3))
        counts = [0, 0, 0]
        for e in range(300):
            counts[route_worker(1, e, 3)] += 1
        self.assertTrue(min(counts) > 50)

    def test_read_expert_roundtrip_and_bank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tensors = {}
            for k, name in enumerate(["gate_proj", "up_proj", "down_proj"]):
                w = f"model.layers.0.mlp.experts.1.{name}.weight"
                q = w + ".qs"
                tensors[w] = bytes([k + 1]) * 16
                tensors[q] = bytes([10 + k]) * 8
            write_safetensors(root / "shard.safetensors", tensors)
            index = index_model(root)
            self.assertEqual(list_expert_ids(index), [(0, 1)])
            blob = read_expert(index, 0, 1)
            self.assertIsNotNone(blob)
            self.assertEqual(len(blob.weight), 48)
            self.assertEqual(len(blob.scales), 24)

            bank = worker_mod.Bank()
            bank.put(0, 1, blob.weight, blob.scales)

            srv = socket.socket()
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", 0))
            port = srv.getsockname()[1]
            srv.listen(1)

            def serve_one():
                conn, _ = srv.accept()
                worker_mod.handle(conn, bank)
                srv.close()

            threading.Thread(target=serve_one, daemon=True).start()
            with socket.create_connection(("127.0.0.1", port), timeout=2) as sock:
                sock.sendall(b"GET 0 1\n")
                f = sock.makefile("rb")
                line = f.readline()
                self.assertTrue(line.startswith(b"OK "))
                _ok, wtot, ftot = line.decode().split()
                data = f.read(int(wtot) + int(ftot) * 4)
            self.assertEqual(data, blob.weight + blob.scales)


if __name__ == "__main__":
    unittest.main()
