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


def lineage_from_artifacts(
    out_dir: Path, dataset_dir: Path, run_id: str | None = None
) -> tuple[list[dict], list[tuple[str, str]], bool]:
    """Replay every task in a run dir through `graph_payload()`, without writing.

    The same reconstruction `main()` replays onto Neo4j, exposed on its own because
    the lineage is a derived index: a reader can render it with no database
    connection at all. Output workbooks are read with `save=False`, so finished
    artifacts are never rewritten, and one unreadable task does not stop the rest.

    Returns `(lineages, skipped, unstamped)`; `skipped` is `[(task_id, reason)]`.
    """
    tasks = {t["id"]: t for t in load_dataset(Path(dataset_dir))}
    lineages: list[dict] = []
    skipped: list[tuple[str, str]] = []
    unstamped = False
    for payload in _payloads(out_dir):
        task_id = payload.get("task_id")
        task = tasks.get(task_id)
        out = _resolve_output(payload, out_dir)
        if task is None or not out.exists():
            why = "not in dataset" if task is None else f"missing output {out}"
            skipped.append((task_id, why))
            continue
        resolved, stamped = _run_id(payload, run_id)
        unstamped = unstamped or not stamped
        try:
            info = read_graded(task, out, save=False)
            lineages.append(
                graph_payload(
                    task,
                    payload.get("status") or "",
                    payload.get("reason") or "",
                    info,
                    payload.get("exceptions") or [],
                    run_id=resolved,
                )
            )
        except Exception as exc:  # noqa: BLE001 — one bad task must not stop the rest
            skipped.append((task_id, f"{type(exc).__name__}: {exc}"))
    return lineages, skipped, unstamped


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

    if not _payloads(out_dir):
        print(f"no exceptions.json or exceptions/*.json under {out_dir}")
        graph.close_graph()
        return 1

    lineages, skipped, unstamped = lineage_from_artifacts(
        out_dir, Path(args.dataset_dir), args.run_id
    )

    replayed = cells = matched = 0
    for task_id, why in skipped:
        print(f"  skip {task_id}: {why}")
    for lineage in lineages:
        if not graph.write_lineage(lineage):
            print(f"  skip {lineage['task_id']}: write_lineage returned False")
            skipped.append((lineage["task_id"], "write_lineage returned False"))
            continue
        replayed += 1
        cells += len(lineage["cells"])
        matched += sum(1 for c in lineage["cells"] if c["vendor_key"])

    graph.close_graph()
    print(f"rebuilt {replayed} task(s), {cells} answer cell(s)")
    if skipped:
        print(f"skipped {len(skipped)}")
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
