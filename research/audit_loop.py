from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from evaluate import score
from sb import load_dataset


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run_dir: Path, dataset_dir: Path) -> dict:
    log_path = run_dir / "loop_log.jsonl"
    logs = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    entries = [entry for entry in logs if "cell_accuracy" in entry]
    if not entries or entries[0]["iter"] != 0:
        raise ValueError("baseline log missing")
    baseline_dir = run_dir / "iter0" / "outputs"
    task_ids = {path.stem for path in baseline_dir.glob("*.xlsx")}
    tasks = [task for task in load_dataset(dataset_dir) if str(task["id"]) in task_ids]
    if len(tasks) != entries[0]["graded"] or len(tasks) != len(task_ids):
        raise ValueError("cannot reconstruct full baseline task set; refusing a partial audit")
    runs = []
    baseline = None
    for entry in entries:
        iteration = entry["iter"]
        output_dir = run_dir / f"iter{iteration}" / "outputs"
        predictions = [{"id": task["id"], "output": str(output_dir / f"{task['id']}.xlsx")} for task in tasks]
        summary, items = score(predictions, tasks, recalc=False)
        if summary["errors"] or summary["missing"] or summary["graded"] != len(tasks):
            raise ValueError(f"iteration {iteration} has missing/error outputs; audit cannot silently exclude them")
        if summary["cell_accuracy"] != entry["cell_accuracy"] or summary["pass_rate"] != entry["pass_rate"]:
            raise ValueError(f"iteration {iteration}: current scorer/artifacts disagree with recorded results")
        by_id = {str(item["id"]): item for item in items}
        if baseline is None:
            baseline = by_id
        total_cells = sum(item["cells"] for item in items)
        task_details = [
            {
                "id": str(item["id"]),
                "cells": item["cells"],
                "correct": item["correct"],
                "passed": item["pass"],
                "accuracy": item["correct"] / item["cells"] if item["cells"] else None,
                "cell_weight": item["cells"] / total_cells,
                "correct_delta_from_baseline": item["correct"] - baseline[str(item["id"])]["correct"],
                "output_sha256": digest(output_dir / f"{item['id']}.xlsx"),
            }
            for item in items
        ]
        if any(item["accuracy"] is None for item in task_details):
            raise ValueError("zero-cell task needs explicit treatment")
        runs.append({
            "iteration": iteration,
            "recorded_decision": entry["decision"],
            "summary": summary,
            "total_cells": total_cells,
            "task_balanced_accuracy": sum(item["accuracy"] for item in task_details) / len(task_details),
            "improved_tasks": sum(item["correct_delta_from_baseline"] > 0 for item in task_details),
            "regressed_tasks": sum(item["correct_delta_from_baseline"] < 0 for item in task_details),
            "tasks": task_details,
        })
    return {
        "purpose": "Read-only audit of existing outputs, no inference or optimization; not a causal replication",
        "recalculation": False,
        "run_dir": str(run_dir.resolve()),
        "log_sha256": digest(log_path),
        "dataset_sha256": digest(dataset_dir / "dataset.json"),
        "scorer_sha256": digest(Path(__file__).with_name("evaluate.py")),
        "value_helpers_sha256": digest(Path(__file__).with_name("sb.py")),
        "reference_hashes": {str(task["id"]): digest(Path(task["golden_xlsx"])) for task in tasks},
        "limitations": [
            "Task set reconstructed from complete baseline outputs and checked against logged graded count",
            "Historical immutable skill snapshots/config manifests absent; no attribution of output changes to skill text",
            "Same development tasks used for mutation and selection",
            "Prior CFO demo use disqualifies it as untouched lockbox",
        ],
        "iterations": runs,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit saved loop outputs without new model calls")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Audit output already exists; reuse the captured evidence or choose a new path")
    result = audit(args.run_dir, args.dataset_dir)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    for iteration in result["iterations"]:
        print(json.dumps({key: value for key, value in iteration.items() if key != "tasks"}))
