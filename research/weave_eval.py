"""Weave Evaluation for tieout — the pipeline as a weave.Model, golden cells as the scorer.

Each dataset row carries the task dict; predict() runs the real pipeline
(verify/repair/fallback loops included, all traced) and the scorer runs
evaluate.score_task against the golden workbook. Usage:

  uv run python weave_eval.py --dataset-dir data/spreadsheetbench_verified_400 \
      --ids-file data/subsample_100_ids.txt --model wandb:meta-llama/Llama-3.3-70B-Instruct
"""

import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT))

import weave
from adapters import make_completer
from evaluate import score_task
from pipeline import _load_env, predict_task
from pydantic import PrivateAttr
from sb import load_dataset, soffice_path
from weave_hooks import init_weave


class TieoutModel(weave.Model):
    """The whole tieout pipeline as the unit under eval — one task in, workbook out."""

    model_spec: str = "wandb:meta-llama/Llama-3.3-70B-Instruct"
    path: str = "hybrid"
    out_dir: str = "/tmp/tieout-eval"
    concurrency: int = 4

    _complete: object = PrivateAttr(default=None)
    _sem: object = PrivateAttr(default=None)

    def _get_complete(self):
        if self._complete is None:
            self._complete = make_completer(self.model_spec)
        return self._complete

    def _get_sem(self):
        if self._sem is None:
            self._sem = asyncio.Semaphore(self.concurrency)
        return self._sem

    @weave.op()
    async def predict(self, task_id: str, task: dict) -> dict:
        out_dir = Path(self.out_dir)
        for sub in ("outputs", "traces", "exceptions"):
            (out_dir / sub).mkdir(parents=True, exist_ok=True)
        result = await predict_task(
            self._get_complete(), task, out_dir, self._get_sem(), path=self.path
        )
        return {"task_id": task_id, "status": result["status"], "output": result["out"]}


@weave.op()
def cell_score(task_id: str, task: dict, output: dict) -> dict:
    """Golden grader: recalc-gated per-cell comparison (evaluate.score_task)."""
    with tempfile.TemporaryDirectory() as work:
        r = score_task(
            task, output.get("output"), recalc=bool(soffice_path()), work_dir=work
        )
    return {
        "passed": bool(r.get("pass")),
        "correct": r.get("correct", 0),
        "cells": r.get("cells", 0),
        "grade_status": r.get("status"),
        "mismatches": r.get("mismatches"),
    }


async def run_eval(model: TieoutModel, tasks: list[dict], name: str):
    rows = [{"task_id": t["id"], "task": t} for t in tasks]
    evaluation = weave.Evaluation(name=name, dataset=rows, scorers=[cell_score])
    return await evaluation.evaluate(model)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weave Evaluation over the tieout pipeline")
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--ids", help="comma-separated task ids")
    p.add_argument("--ids-file", help="file with one task id per line")
    p.add_argument("--sample", type=int, help="first N tasks")
    p.add_argument("--model", default=TieoutModel.model_fields["model_spec"].default)
    p.add_argument("--path", default="hybrid")
    p.add_argument("--out-dir", default="/tmp/tieout-eval")
    p.add_argument("--name", default="tieout-eval")
    p.add_argument("--concurrency", type=int, default=4)
    return p.parse_args()


def select_tasks(dataset_dir: str, args) -> list[dict]:
    tasks = load_dataset(dataset_dir)
    ids = None
    if args.ids:
        ids = {i.strip() for i in args.ids.split(",") if i.strip()}
    elif args.ids_file:
        ids = {
            ln.strip() for ln in Path(args.ids_file).read_text().splitlines() if ln.strip()
        }
    if ids is not None:
        tasks = [t for t in tasks if t["id"] in ids]
    if args.sample:
        tasks = tasks[: args.sample]
    return tasks


async def amain() -> None:
    args = parse_args()
    _load_env()
    if not init_weave():
        raise SystemExit("weave unavailable — set WANDB_API_KEY (TIEOUT_WEAVE=0 disables)")
    tasks = select_tasks(args.dataset_dir, args)
    print(f"evaluating {len(tasks)} tasks -> {args.out_dir}")
    model = TieoutModel(
        model_spec=args.model,
        path=args.path,
        out_dir=args.out_dir,
        concurrency=args.concurrency,
    )
    summary = await run_eval(model, tasks, args.name)
    print(summary)


if __name__ == "__main__":
    asyncio.run(amain())
