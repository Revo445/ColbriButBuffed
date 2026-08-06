#!/usr/bin/env python3
"""Plan expert→worker assignment for COLI_RAM_BANK."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ram_pool import route_worker  # noqa: E402


def main(argv=None):
    p = argparse.ArgumentParser(description="ColbriButBuffed RAM-pool coordinator")
    p.add_argument("--experts", type=int, default=19456,
                   help="Routed experts per layer count used for coverage estimate "
                        "(GLM-5.2 = 256 experts × layers; pass total expert slots if known)")
    p.add_argument("--layers", type=int, default=76, help="Sparse layers (GLM-5.2 ≈ 76)")
    p.add_argument("--node", action="append", default=[],
                   help="host:port=budget_gb or host=budget_gb (port default 9400)")
    p.add_argument("--bytes-per-expert", type=float, default=19.0,
                   help="Approx MiB per expert slab+scales (int4 GLM ~19)")
    args = p.parse_args(argv)
    if not args.node:
        p.error("pass at least one --node host=budget_gb")

    nodes = []
    for spec in args.node:
        left, _, budget_s = spec.partition("=")
        if not budget_s:
            p.error(f"bad --node {spec} (want host=gb or host:port=gb)")
        if ":" in left and left.rsplit(":", 1)[-1].isdigit():
            endpoint = left
        else:
            endpoint = f"{left}:9400"
        nodes.append((endpoint, float(budget_s)))

    total_budget = sum(b for _, b in nodes)
    mib = args.bytes_per_expert
    capacity = int((total_budget * 1024) / mib)
    total_slots = args.layers * 256  # GLM-style; --experts overrides coverage denom if set
    denom = args.experts if args.experts > 0 else total_slots

    print("ColbriButBuffed RAM pool plan")
    print(f"  nodes:           {len(nodes)}")
    print(f"  pooled budget:   {total_budget:.1f} GiB")
    print(f"  ~expert capacity:{capacity} (at {mib} MiB each)")
    print(f"  coverage hint:   {min(100.0, 100.0 * capacity / max(denom, 1)):.1f}% of {denom} slots")
    print()
    print("Worker env examples:")
    for i, (endpoint, budget) in enumerate(nodes):
        host = endpoint.rsplit(":", 1)[0]
        port = endpoint.rsplit(":", 1)[1]
        print(f"  # worker {i} on {endpoint}")
        print(f"  WORKER_INDEX={i} WORKER_COUNT={len(nodes)} BUDGET_GB={budget} "
              f"BIND=0.0.0.0:{port} MODEL=/models/glm52_i4 \\")
        print(f"    python3 tools/ram_pool/worker.py")
    print()
    banks = ",".join(ep for ep, _ in nodes)
    print("Primary:")
    print(f"  export COLI_RAM_BANK={banks}")
    print("  python3 coli serve --model /models/glm52_i4 --policy lowspec --host 0.0.0.0")
    print()
    # Show hash balance
    counts = [0] * len(nodes)
    sample_layers = min(args.layers, 8)
    for layer in range(sample_layers):
        for eid in range(256):
            counts[route_worker(layer, eid, len(nodes))] += 1
    print(f"Hash balance over first {sample_layers} layers × 256 experts: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
