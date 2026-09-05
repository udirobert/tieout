"""Restitch hybrid-v2: existing hybrid + pin-fix overlays for the 27 cell-dip ids.

  python3 research/stitch_hybrid_v2.py \
    --base /tmp/tinker-400-hybrid \
    --overlay /tmp/tinker-cell-dip-pin \
    --out /tmp/tinker-400-hybrid-v2 \
    --ids-file research/data/cell_dip_ids.txt
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def _ids(path: Path) -> list[str]:
    raw = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        raw.extend(x.strip() for x in line.split(",") if x.strip())
    return raw


def _pred_map(path: Path) -> dict[str, dict]:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        out[str(row["id"])] = row
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="/tmp/tinker-400-hybrid")
    p.add_argument("--overlay", default="/tmp/tinker-cell-dip-pin")
    p.add_argument("--out", default="/tmp/tinker-400-hybrid-v2")
    p.add_argument("--ids-file", default="research/data/cell_dip_ids.txt")
    args = p.parse_args()

    base = Path(args.base)
    overlay = Path(args.overlay)
    dest = Path(args.out)
    ids = _ids(Path(args.ids_file))
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base, dest)

    base_preds = _pred_map(dest / "predictions.jsonl")
    over_preds = _pred_map(overlay / "predictions.jsonl")
    missing = []
    for tid in ids:
        src = overlay / "outputs" / f"{tid}.xlsx"
        if not src.exists():
            missing.append(tid)
            continue
        shutil.copy2(src, dest / "outputs" / f"{tid}.xlsx")
        tsrc = overlay / "traces" / f"{tid}.jsonl"
        if tsrc.exists():
            shutil.copy2(tsrc, dest / "traces" / f"{tid}.jsonl")
        if tid in over_preds:
            base_preds[tid] = over_preds[tid]
    (dest / "predictions.jsonl").write_text(
        "".join(json.dumps(base_preds[k]) + "\n" for k in base_preds)
    )
    note = dest / "STITCH.txt"
    note.write_text(
        f"hybrid-v2 stitch\nbase={base}\noverlay={overlay}\n"
        f"overlaid={len(ids) - len(missing)} missing={missing}\n"
    )
    print(f"wrote {dest} overlaid {len(ids) - len(missing)}/{len(ids)}")
    if missing:
        raise SystemExit(f"missing overlay outputs: {missing}")


if __name__ == "__main__":
    main()
