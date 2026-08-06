#!/usr/bin/env python3
"""RAM-pool worker: mlock expert weight slabs and serve them over TCP."""

from __future__ import annotations

import os
import socket
import struct
import sys
import threading
from pathlib import Path

# Allow `python3 tools/ram_pool/worker.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ram_pool import (  # noqa: E402
    env_budget_bytes,
    index_model,
    list_expert_ids,
    read_expert,
    route_worker,
    try_mlock,
)


def _parse_bind(raw: str) -> tuple[str, int]:
    host, _, port = raw.rpartition(":")
    return (host or "0.0.0.0"), int(port or "9400")


class Bank:
    def __init__(self):
        self._lock = threading.Lock()
        self.blobs: dict[tuple[int, int], tuple[bytes, bytes]] = {}

    def put(self, layer: int, eid: int, weight: bytes, scales: bytes):
        with self._lock:
            self.blobs[(layer, eid)] = (weight, scales)

    def get(self, layer: int, eid: int):
        with self._lock:
            return self.blobs.get((layer, eid))


def handle(conn: socket.socket, bank: Bank):
    with conn:
        f = conn.makefile("rwb")
        line = f.readline()
        if not line:
            return
        parts = line.decode("ascii", errors="replace").strip().split()
        if len(parts) != 3 or parts[0] != "GET":
            f.write(b"ERR bad request\n")
            f.flush()
            return
        layer, eid = int(parts[1]), int(parts[2])
        blob = bank.get(layer, eid)
        if blob is None:
            f.write(b"ERR miss\n")
            f.flush()
            return
        weight, scales = blob
        ftot = len(scales) // 4
        f.write(f"OK {len(weight)} {ftot}\n".encode("ascii"))
        f.flush()
        f.write(weight)
        f.write(scales)
        f.flush()


def main():
    model = Path(os.environ.get("MODEL", ".")).resolve()
    bind = os.environ.get("BIND", "0.0.0.0:9400")
    worker_index = int(os.environ.get("WORKER_INDEX", "0"))
    worker_count = int(os.environ.get("WORKER_COUNT", "1"))
    budget = env_budget_bytes()

    print(f"[ram_pool] indexing {model}", flush=True)
    index = index_model(model)
    experts = list_expert_ids(index)
    mine = [(L, e) for (L, e) in experts if route_worker(L, e, worker_count) == worker_index]
    print(f"[ram_pool] {len(experts)} experts total; {len(mine)} routed to worker "
          f"{worker_index}/{worker_count}; budget {budget / (1 << 30):.2f} GiB", flush=True)

    bank = Bank()
    used = 0
    locked = 0
    for layer, eid in mine:
        blob = read_expert(index, layer, eid)
        if blob is None:
            continue
        need = len(blob.weight) + len(blob.scales)
        if used + need > budget:
            break
        # Keep a single bytearray for optional mlock of the weight slab.
        buf = bytearray(blob.weight)
        if try_mlock(buf):
            locked += 1
        bank.put(layer, eid, bytes(buf), blob.scales)
        used += need

    print(f"[ram_pool] resident experts={len(bank.blobs)} bytes={used} mlock_ok={locked}",
          flush=True)

    host, port = _parse_bind(bind)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(128)
    print(f"[ram_pool] listening on {host}:{port}", flush=True)
    while True:
        conn, _addr = sock.accept()
        threading.Thread(target=handle, args=(conn, bank), daemon=True).start()


if __name__ == "__main__":
    main()
