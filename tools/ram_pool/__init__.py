#!/usr/bin/env python3
"""Shared helpers for ColbriButBuffed RAM pool (expert weight bank)."""

from __future__ import annotations

import json
import os
import struct
from dataclasses import dataclass
from pathlib import Path


def route_worker(layer: int, eid: int, n: int) -> int:
    if n <= 0:
        raise ValueError("n must be > 0")
    return (layer * 1315423911 + eid) % n


@dataclass(frozen=True)
class TensorLoc:
    path: Path
    offset: int
    nbytes: int


@dataclass
class ExpertBlob:
    layer: int
    eid: int
    weight: bytes  # contiguous gate/up/down by file offset order
    scales: bytes  # concatenated .qs payloads in same component order as weight


def _parse_header(path: Path) -> dict[str, TensorLoc]:
    with path.open("rb") as f:
        (hlen,) = struct.unpack("<Q", f.read(8))
        raw = f.read(hlen)
    meta = json.loads(raw.decode("utf-8"))
    out: dict[str, TensorLoc] = {}
    for name, info in meta.items():
        if name == "__metadata__":
            continue
        off0, off1 = info["data_offsets"]
        out[name] = TensorLoc(path, 8 + hlen + int(off0), int(off1) - int(off0))
    return out


def index_model(model_dir: Path) -> dict[str, TensorLoc]:
    model_dir = Path(model_dir)
    index: dict[str, TensorLoc] = {}
    shards = sorted(model_dir.glob("*.safetensors"))
    if not shards:
        raise FileNotFoundError(f"no .safetensors under {model_dir}")
    for shard in shards:
        index.update(_parse_header(shard))
    return index


def expert_names(layer: int, eid: int) -> list[str]:
    return [
        f"model.layers.{layer}.mlp.experts.{eid}.gate_proj.weight",
        f"model.layers.{layer}.mlp.experts.{eid}.up_proj.weight",
        f"model.layers.{layer}.mlp.experts.{eid}.down_proj.weight",
    ]


def read_expert(index: dict[str, TensorLoc], layer: int, eid: int) -> ExpertBlob | None:
    names = expert_names(layer, eid)
    tw = []
    tq = []
    for name in names:
        w = index.get(name)
        q = index.get(name + ".qs")
        if not w or not q:
            return None
        tw.append(w)
        tq.append(q)
    # Weights: file-offset order (matches engine coalesced pread into slab).
    order = sorted(range(3), key=lambda i: (str(tw[i].path), tw[i].offset))
    weight_parts = []
    for i in order:
        loc = tw[i]
        with loc.path.open("rb") as f:
            f.seek(loc.offset)
            weight_parts.append(f.read(loc.nbytes))
    # Scales: gate/up/down order (engine fp[k] for k=0..2).
    scale_parts = []
    for q in tq:
        with q.path.open("rb") as f:
            f.seek(q.offset)
            scale_parts.append(f.read(q.nbytes))
    return ExpertBlob(layer, eid, b"".join(weight_parts), b"".join(scale_parts))


def list_expert_ids(index: dict[str, TensorLoc]) -> list[tuple[int, int]]:
    found: set[tuple[int, int]] = set()
    prefix = "model.layers."
    mid = ".mlp.experts."
    for name in index:
        if not name.endswith(".gate_proj.weight"):
            continue
        if prefix not in name or mid not in name:
            continue
        try:
            rest = name[len(prefix):]
            layer_s, rest = rest.split(mid, 1)
            eid_s = rest.split(".", 1)[0]
            found.add((int(layer_s), int(eid_s)))
        except ValueError:
            continue
    return sorted(found)


def try_mlock(buf: bytearray | memoryview) -> bool:
    try:
        import ctypes
        libc = ctypes.CDLL(None)
        ptr = ctypes.addressof(ctypes.c_char.from_buffer(buf))
        return libc.mlock(ctypes.c_void_p(ptr), ctypes.c_size_t(len(buf))) == 0
    except Exception:
        return False


def env_budget_bytes() -> int:
    gb = float(os.environ.get("BUDGET_GB", "4"))
    return int(gb * (1 << 30))
