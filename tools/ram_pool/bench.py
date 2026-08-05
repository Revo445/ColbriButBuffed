#!/usr/bin/env python3
"""Compare local safetensors pread vs RAM-bank fetch latency."""

from __future__ import annotations

import argparse
import socket
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ram_pool import index_model, list_expert_ids, read_expert  # noqa: E402


def bank_get(host: str, port: int, layer: int, eid: int, timeout: float = 5.0):
    t0 = time.perf_counter()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(f"GET {layer} {eid}\n".encode("ascii"))
        f = sock.makefile("rb")
        line = f.readline()
        if not line.startswith(b"OK "):
            return None, time.perf_counter() - t0
        _ok, wtot_s, ftot_s = line.decode().split()
        wtot, ftot = int(wtot_s), int(ftot_s)
        payload = f.read(wtot + ftot * 4)
        if len(payload) != wtot + ftot * 4:
            return None, time.perf_counter() - t0
    return len(payload), time.perf_counter() - t0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--bank", required=True, help="host:port")
    p.add_argument("--samples", type=int, default=16)
    args = p.parse_args(argv)
    host, port_s = args.bank.rsplit(":", 1)
    port = int(port_s)

    index = index_model(Path(args.model))
    experts = list_expert_ids(index)
    if not experts:
        print("no experts found", file=sys.stderr)
        return 1

    local_ms = []
    bank_ms = []
    hits = 0
    for i in range(args.samples):
        layer, eid = experts[i % len(experts)]
        t0 = time.perf_counter()
        blob = read_expert(index, layer, eid)
        local_ms.append((time.perf_counter() - t0) * 1000)
        nbytes, dt = bank_get(host, port, layer, eid)
        bank_ms.append(dt * 1000)
        if nbytes:
            hits += 1
        print(f"  expert {layer}/{eid}: local {local_ms[-1]:.1f} ms  bank {bank_ms[-1]:.1f} ms  "
              f"{'hit' if nbytes else 'miss'}")

    print()
    print(f"local median {statistics.median(local_ms):.1f} ms")
    print(f"bank  median {statistics.median(bank_ms):.1f} ms  hits {hits}/{args.samples}")
    if statistics.median(bank_ms) > statistics.median(local_ms) * 1.5:
        print("Verdict: bank slower than local reads — use pool mainly if primary is swapping,")
        print("or move to faster interconnect / remote-compute workers (see docs/pooled-ram.md).")
    else:
        print("Verdict: bank competitive on this fabric for these samples.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
