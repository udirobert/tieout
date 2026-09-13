#!/usr/bin/env python3
"""Rebuild the tieout lineage graph from artifacts already on disk.

The graph is a derived index, never the system of record: every node and edge it
holds is reconstructible from a run's exceptions.json + outputs/*.xlsx + the
dataset. Run this when a free Aura instance has auto-paused or been deleted, or to
move a run's lineage onto a different Neo4j backend.

Idempotent — each task replays onto the run_id stamped in its payload, so
re-running collapses instead of growing. MATCHES edges are resolved by OPTIONAL
MATCH, so seeding the vendor master afterwards and re-running adds them without
duplicating anything.

Usage:
  cd research && uv run --extra graph python ../demo/rebuild_graph.py <out_dir>
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))

import graph  # noqa: E402
from exceptions import graph_payload  # noqa: E402
from pipeline import read_graded  # noqa: E402
from sb import load_dataset  # noqa: E402

DEFAULT_DATASET = ROOT / "demo/close-tieout"


def _payloads(out_dir: Path) -> list[dict]:
    """Aggregate exceptions.json when present, else the per-task files."""
    agg = out_dir / "exceptions.json"
    if agg.exists():
        data = json.loads(agg.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        if rows:
            return rows
    rows = []
    for path in sorted((out_dir / "exceptions").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.extend(data if isinstance(data, list) else [data])
    return rows


def _run_id(payload: dict, override: str | None) -> tuple[str, bool]:
    """(run_id, stamped). Unstamped artifacts predate the stamp in exceptions.py."""
    if override:
        return override, True
    stamped = (payload.get("graph") or {}).get("run_id")
    if stamped:
        return str(stamped), True
    return graph.run_id(), False


def _resolve_output(payload: dict, out_dir: Path) -> Path:
    """Prefer the recorded absolute path, else this run dir's own outputs/ copy.

    exceptions.json stores absolute paths, so artifacts copied to another machine
    would otherwise be unreplayable.
    """
    recorded = Path(payload.get("output") or "")
    if recorded.exists():
        return recorded
    return out_dir / "outputs" / f"{payload.get('task_id')}.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out_dir", help="run dir holding exceptions.json + outputs/")
    parser.add_argument("--dataset-dir", default=str(DEFAULT_DATASET))
    parser.add_argument(
        "--run-id",
        default=None,
        help="replay every task onto this run_id (default: the stamped one)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.is_dir():
        print(f"not a directory: {out_dir}")
        return 1
    if not graph.init_graph():
        print(
            "graph disabled — set NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD in .env, and "
            "resume the Aura instance if it auto-paused."
        )
        return 1

    rows = _payloads(out_dir)
    if not rows:
        print(f"no exceptions.json or exceptions/*.json under {out_dir}")
        graph.close_graph()
        return 1
    tasks = {t["id"]: t for t in load_dataset(Path(args.dataset_dir))}

    replayed = skipped = cells = matched = 0
    unstamped = False
    for payload in rows:
        task_id = payload.get("task_id")
        task = tasks.get(task_id)
        out = _resolve_output(payload, out_dir)
        if task is None or not out.exists():
            why = "not in dataset" if task is None else f"missing output {out}"
            print(f"  skip {task_id}: {why}")
            skipped += 1
            continue
        run_id, stamped = _run_id(payload, args.run_id)
        unstamped = unstamped or not stamped
        try:
            # save=False: a replay reads finished artifacts, it never rewrites them.
            info = read_graded(task, out, save=False)
            lineage = graph_payload(
                task,
                payload.get("status") or "",
                payload.get("reason") or "",
                info,
                payload.get("exceptions") or [],
                run_id=run_id,
            )
            ok = graph.write_lineage(lineage)
        except Exception as exc:  # noqa: BLE001 — one bad task must not stop the rest
            print(f"  skip {task_id}: {type(exc).__name__}: {exc}")
            skipped += 1
            continue
        if not ok:
            print(f"  skip {task_id}: write_lineage returned False")
            skipped += 1
            continue
        replayed += 1
        cells += len(lineage["cells"])
        matched += sum(1 for c in lineage["cells"] if c["vendor_key"])

    graph.close_graph()
    print(f"rebuilt {replayed} task(s), {cells} answer cell(s)")
    if skipped:
        print(f"skipped {skipped}")
    if matched:
        print(
            f"{matched} cell(s) carry a vendor_key; a MATCHES edge exists only where "
            "that key is in the seeded vendor master (demo/seed_graph.py)."
        )
    if unstamped and not args.run_id:
        print(
            "warning: some artifacts predate the run_id stamp and replayed onto the "
            "current TIEOUT_RUN_ID — pass --run-id to pin it."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
