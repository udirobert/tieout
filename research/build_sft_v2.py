"""Build v2 SFT set with a target sheet/cell mix.

Usage:
  python research/build_sft_v2.py \
      --trajectories research/data/sft/trajectories.jsonl \
      --out-dir research/data/sft \
      --target-sheet 0.60 \
      --max-per-task 2
"""

import argparse
import datetime
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_v2(trajectories: Path, out_dir: Path, target_sheet: float, max_per_task: int):
    records_by_task: dict[str, list[dict]] = defaultdict(list)
    seen = set()
    for line in trajectories.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        key = (r["id"], r["completion"])
        if key in seen:
            continue
        seen.add(key)
        records_by_task[r["id"]].append(r)

    # cap per task, but separate by kind so we can balance later
    sheet, cell = [], []
    for _id, recs in records_by_task.items():
        for r in recs[:max_per_task]:
            if r["kind"] == "sheet-level":
                sheet.append(r)
            else:
                cell.append(r)

    # maximize total while hitting the target ratio, keeping as many sheet
    # records as possible (the scarce class) and taking the matching number of
    # cell records.
    n_sheet = len(sheet)
    n_cell = len(cell)
    # sheet / (sheet + cell) = target_sheet  =>  cell = sheet * (1-target)/target
    needed_cell_from_sheet = int(round(n_sheet * (1 - target_sheet) / target_sheet))
    # total <= min(sheet, cell limit)
    if needed_cell_from_sheet <= n_cell:
        chosen = sheet + cell[:needed_cell_from_sheet]
    else:
        # not enough cells; take all cells and matching sheet count
        n_sheet = int(round(n_cell * target_sheet / (1 - target_sheet)))
        chosen = sheet[:n_sheet] + cell

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sft_train_v2.jsonl"
    with out_path.open("w") as f:
        for r in chosen:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest = {
        "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "git_sha": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT
        ).stdout.strip(),
        "target_sheet_ratio": target_sheet,
        "max_per_task": max_per_task,
        "total_verified": sum(len(recs) for recs in records_by_task.values()),
        "kept": len(chosen),
        "cell_level": len([r for r in chosen if r["kind"] == "cell-level"]),
        "sheet_level": len([r for r in chosen if r["kind"] == "sheet-level"]),
        "tasks_with_trajectory": len(records_by_task),
        "in_tokens": sum(r.get("in_tokens") or 0 for r in chosen),
        "out_tokens": sum(r.get("out_tokens") or 0 for r in chosen),
    }
    (out_dir / "sft_manifest_v2.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--trajectories", default="research/data/sft/trajectories.jsonl")
    p.add_argument("--out-dir", default="research/data/sft")
    p.add_argument("--target-sheet", type=float, default=0.60)
    p.add_argument("--max-per-task", type=int, default=2)
    args = p.parse_args()
    build_v2(Path(args.trajectories), Path(args.out_dir), args.target_sheet, args.max_per_task)


if __name__ == "__main__":
    main()
