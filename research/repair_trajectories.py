"""In-place repair of trajectories.jsonl completions.

Canonicalizes every completion to a compact, sorted-by-ref JSON form and drops
records that still exceed MAX_COMPLETION_LEN, contain think tags, or fail to
parse. Emits:

  trajectories.jsonl.repaired   - clean records
  trajectories.jsonl.rejected   - records that failed the gate
  repair_manifest.json          - counts + stats

Usage:
  python research/repair_trajectories.py --out-dir research/data/sft [--swap]
"""

import argparse
import json
import shutil
import time
from collections import Counter
from pathlib import Path

MAX_COMPLETION_LEN = 8000


def _cell_sort_key(c: dict) -> tuple:
    col = c.get("cell", "")
    # split "A2" -> (col_part, row_part)
    row = ""
    col_part = ""
    for ch in col:
        if ch.isdigit():
            row += ch
        else:
            col_part += ch
    return (c.get("sheet", "") or "", col_part, int(row) if row.isdigit() else 0)


def canonicalize(completion: str) -> str:
    obj = json.loads(completion)
    cells = obj.get("cells", [])
    # ensure scalar values and sort deterministically
    for c in cells:
        v = c.get("value")
        if isinstance(v, float) and v.is_integer():
            c["value"] = int(v)
    cells.sort(key=_cell_sort_key)
    return json.dumps({"cells": cells}, ensure_ascii=False, separators=(",", ":"))


def repair(out_dir: Path, swap: bool = False) -> dict:
    traj_path = out_dir / "trajectories.jsonl"
    repaired_path = out_dir / "trajectories.jsonl.repaired"
    rejected_path = out_dir / "trajectories.jsonl.rejected"

    if not traj_path.exists():
        raise FileNotFoundError(traj_path)

    kept, rejected = [], []
    stats = Counter({"total": 0, "kept": 0, "rejected": 0, "too_long": 0, "bad_json": 0, "think_leak": 0})
    lens = []

    for line in traj_path.read_text().splitlines():
        if not line.strip():
            continue
        stats["total"] += 1
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            stats["bad_json"] += 1
            stats["rejected"] += 1
            rejected.append(line)
            continue

        completion = r.get("completion", "")
        if not isinstance(completion, str):
            completion = json.dumps(completion, ensure_ascii=False, separators=(",", ":"))

        try:
            clean = canonicalize(completion)
        except (json.JSONDecodeError, ValueError, KeyError):
            stats["bad_json"] += 1
            stats["rejected"] += 1
            rejected.append(json.dumps(r, ensure_ascii=False))
            continue

        think_tags = ("\x3cthinking\x3e", "\x3c/thinking\x3e")
        if any(tag in clean for tag in think_tags):
            stats["think_leak"] += 1
            stats["rejected"] += 1
            rejected.append(json.dumps({**r, "completion": clean}, ensure_ascii=False))
            continue

        if len(clean) > MAX_COMPLETION_LEN:
            stats["too_long"] += 1
            stats["rejected"] += 1
            rejected.append(json.dumps({**r, "completion": clean}, ensure_ascii=False))
            continue

        r["completion"] = clean
        kept.append(json.dumps(r, ensure_ascii=False))
        lens.append(len(clean))
        stats["kept"] += 1

    repaired_path.write_text("\n".join(kept) + ("\n" if kept else ""))
    rejected_path.write_text("\n".join(rejected) + ("\n" if rejected else ""))

    manifest = {
        "max_completion_len": MAX_COMPLETION_LEN,
        "total": stats["total"],
        "kept": stats["kept"],
        "rejected": stats["rejected"],
        "too_long": stats["too_long"],
        "bad_json": stats["bad_json"],
        "think_leak": stats["think_leak"],
        "mean_len": int(sum(lens) / len(lens)) if lens else 0,
        "max_len": max(lens) if lens else 0,
        "min_len": min(lens) if lens else 0,
        "repaired_path": str(repaired_path),
        "rejected_path": str(rejected_path),
    }
    (out_dir / "repair_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if swap:
        ts = int(time.time())
        backup = out_dir / f"trajectories.jsonl.bak.{ts}"
        shutil.move(str(traj_path), str(backup))
        shutil.move(str(repaired_path), str(traj_path))
        manifest["swapped"] = True
        manifest["backup"] = str(backup)
    else:
        manifest["swapped"] = False

    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="research/data/sft")
    p.add_argument("--swap", action="store_true")
    args = p.parse_args()

    manifest = repair(Path(args.out_dir), swap=args.swap)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
