"""Restitch hybrid: new values-first cell outputs + existing codegen sheets.

  python3 research/stitch_hybrid_pin.py \
    --sheets /tmp/tinker-400-codegen \
    --cells /tmp/tinker-400-values-pin \
    --out /tmp/tinker-400-hybrid-pin
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))

from prompts import classify  # noqa: E402
from sb import load_dataset  # noqa: E402


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
    p.add_argument("--sheets", default="/tmp/tinker-400-codegen")
    p.add_argument("--cells", default="/tmp/tinker-400-values-pin")
    p.add_argument("--out", default="/tmp/tinker-400-hybrid-pin")
    p.add_argument(
        "--dataset-dir",
        default=str(ROOT / "research/data/spreadsheetbench_verified_400"),
    )
    args = p.parse_args()
    dataset = Path(args.dataset_dir)
    if not dataset.exists():
        dataset = Path.home() / "tieout/research/data/spreadsheetbench_verified_400"

    sheets = Path(args.sheets)
    cells = Path(args.cells)
    dest = Path(args.out)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(sheets, dest)

    tasks = load_dataset(dataset)
    preds = _pred_map(dest / "predictions.jsonl")
    cell_preds = _pred_map(cells / "predictions.jsonl")
    n_cell = n_sheet = missing = 0
    for task in tasks:
        tid = task["id"]
        if classify(task) == "sheet-level":
            n_sheet += 1
            continue
        src = cells / "outputs" / f"{tid}.xlsx"
        if not src.exists():
            missing += 1
            continue
        shutil.copy2(src, dest / "outputs" / f"{tid}.xlsx")
        tsrc = cells / "traces" / f"{tid}.jsonl"
        if tsrc.exists():
            (dest / "traces").mkdir(exist_ok=True)
            shutil.copy2(tsrc, dest / "traces" / f"{tid}.jsonl")
        if tid in cell_preds:
            preds[tid] = cell_preds[tid]
        n_cell += 1
    (dest / "predictions.jsonl").write_text(
        "".join(json.dumps(preds[k]) + "\n" for k in preds)
    )
    (dest / "STITCH.txt").write_text(
        f"hybrid-pin stitch\nsheets={sheets}\ncells={cells}\n"
        f"overlaid_cells={n_cell} sheets_kept={n_sheet} missing={missing}\n"
    )
    print(f"wrote {dest} cells={n_cell} sheets={n_sheet} missing={missing}")
    if missing:
        raise SystemExit(f"missing {missing} cell outputs")


if __name__ == "__main__":
    main()
