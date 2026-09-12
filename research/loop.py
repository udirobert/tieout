"""tieout self-improvement loop — the CoreWeave Hacks delta.

Each iteration: run the pipeline on the eval split → score against goldens →
cluster failures by signature → a mutator agent (W&B Inference) edits the
agent's own skill library (harness/skills_overlay.json) → re-score → keep the
change on improvement, revert on regression. Hill-climbing on cell_accuracy,
every iteration logged to Weave and out_dir/loop_log.jsonl.

  uv run python loop.py --dataset-dir data/spreadsheetbench_verified_400 \
      --sample 20 --iters 4 --model wandb:meta-llama/Llama-3.3-70B-Instruct
"""

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT))

from adapters import make_completer
from pipeline import _load_env, predict_task
from skills import load_overlay
from weave_hooks import enabled as weave_on
from weave_hooks import init_weave, traceable

from evaluate import score
from sb import load_dataset, soffice_path

OVERLAY_PATH = ROOT / "harness" / "skills_overlay.json"

MUTATE_SYSTEM = (
    "You improve a spreadsheet-reconciliation agent by editing its skill "
    "library. The agent injects 'domain skill' fragments into its code-"
    "generation prompt, selected by keyword match on the task instruction. "
    "You see clustered eval failures and propose better skill text. Reply "
    "with JSON only."
)

MUTATE_PROMPT = """## Current skill overlay (learned so far; may be empty)
{overlay}

## Base skills that can be replaced by name
LOOKUP_SKILL, AGGREGATION_SKILL, SHEET_REORG_SKILL, FILL_GATED_SKILL, DATE_TIME_SKILL, RECONCILIATION_SKILL

## Failures from the latest eval, clustered
{clusters}

Propose an updated overlay targeting the biggest failure class. Rules:
- Generic procedural guidance only — never task ids, cell coordinates, or dataset values.
- One high-impact fix beats many speculative ones; at most 3 skill entries.
- JSON only: {{"skills": [{{"name": str, "keywords": [str], "text": str, "replaces": null|<BASE_NAME>}}], "rationale": str}}
- "keywords" gate when the skill applies (lowercase substring match on the instruction); new skills MUST have at least one keyword — always-on skills are dropped.
- "replaces" swaps a base skill for your improved text (replaces inherits the base skill's gating).
- Keep "text" under 1500 chars; a few precise rules beat a wall of edge cases.
- If no fix is credible, return {{"skills": {overlay_empty}, "rationale": "no credible fix"}}."""


def _load_env_and_weave():
    _load_env()
    init_weave()


def _snapshot_overlay() -> list[dict]:
    return load_overlay()


def _write_overlay(entries: list[dict]) -> None:
    OVERLAY_PATH.write_text(
        json.dumps({"skills": entries}, indent=2) + "\n", encoding="utf-8"
    )


def _task_dirs(out_dir: Path) -> None:
    for sub in ("outputs", "traces", "exceptions"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)


async def _run_pipeline(
    complete, tasks: list[dict], iter_dir: Path, path: str, concurrency: int
) -> None:
    _task_dirs(iter_dir)
    sem = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(
        *(predict_task(complete, t, iter_dir, sem, path=path) for t in tasks)
    )
    with (iter_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for t, r in zip(tasks, results):
            f.write(json.dumps({"id": t["id"], "output": r["out"], "status": r["status"]}) + "\n")


async def run_iteration(
    complete,
    model_spec: str,
    tasks: list[dict],
    iter_dir: Path,
    path: str,
    concurrency: int,
    use_weave: bool,
    iter_name: str,
) -> tuple[dict, list[dict]]:
    """Run + score one iteration. Returns (summary, items) from the golden grader."""
    if use_weave:
        from weave_eval import TieoutModel, run_eval

        model = TieoutModel(
            model_spec=model_spec,
            path=path,
            out_dir=str(iter_dir),
            concurrency=concurrency,
        )
        model._complete = complete  # reuse the same traced completer
        await run_eval(model, tasks, iter_name)
    else:
        await _run_pipeline(complete, tasks, iter_dir, path, concurrency)

    preds = [
        {"id": t["id"], "output": str(iter_dir / "outputs" / f"{t['id']}.xlsx")}
        for t in tasks
    ]
    summary, items = score(
        preds, tasks, recalc=bool(soffice_path()), predictions_path=iter_dir
    )
    return summary, items


def cluster_failures(items: list[dict], tasks_by_id: dict) -> list[dict]:
    """Group failed tasks by (instruction_type, failure signature)."""
    clusters: dict = {}
    for it in items:
        if it.get("pass") or it.get("status") == "no_golden":
            continue
        task = tasks_by_id.get(it["id"], {})
        sig = it.get("status", "?")
        if sig == "graded":
            sig = "wrong values"
        elif sig in ("missing", "missing_output"):
            sig = "no output"
        key = (task.get("instruction_type") or "?", sig)
        ex = {
            "instruction": (task.get("instruction") or "")[:400],
            "status": it.get("status"),
        }
        if it.get("mismatches"):
            ex["mismatches"] = it["mismatches"][:3]
        clusters.setdefault(key, []).append(ex)
    return [
        {"instruction_type": k[0], "signature": k[1], "count": len(v), "examples": v[:3]}
        for k, v in sorted(clusters.items(), key=lambda kv: -len(kv[1]))
    ]


MUTATE_REPAIR = (
    "Your previous reply failed to parse ({error}). Reply with ONLY the "
    "corrected JSON object, same schema as before.\n\nPrevious reply:\n{reply}"
)


def _parse_overlay(text: str) -> tuple[list[dict] | None, str]:
    """(skills, rationale) on success; (None, error) on failure."""
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        return None, "mutator returned no JSON"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, "mutator JSON did not parse"
    skills = obj.get("skills")
    if not isinstance(skills, list):
        return None, "mutator JSON missing skills list"
    clean = []
    for e in skills:
        if not isinstance(e, dict):
            continue
        text = (e.get("text") or "").strip()
        # Prompt bloat / negative-transfer guards (Decagon GEPA study):
        # cap fragment length; learned skills must be keyword-gated —
        # only a "replaces" entry may go always-on (it inherits base gating).
        if not text or len(text) > 1500:
            continue
        if not e.get("replaces") and not e.get("keywords"):
            continue
        clean.append(e)
    return clean[:3], (obj.get("rationale") or "")[:300]


@traceable("propose_overlay")
async def propose_overlay(
    mutator, clusters: list[dict], current: list[dict]
) -> tuple[list[dict] | None, str]:
    """Mutator agent: failure clusters -> new skills_overlay entries (or None).

    One repair attempt on parse failure — fail loudly, not silently.
    """
    prompt = MUTATE_PROMPT.format(
        overlay=json.dumps(current, indent=2)[:4000],
        overlay_empty=json.dumps(current),
        clusters=json.dumps(clusters, indent=2)[:8000],
    )
    last_err = "no attempt"
    for _ in range(2):
        text, _, _ = await mutator(prompt, MUTATE_SYSTEM)
        skills, msg = _parse_overlay(text)
        if skills is not None:
            return skills, msg
        last_err = msg
        prompt = MUTATE_REPAIR.format(error=msg, reply=(text or "")[:4000])
    return None, last_err


def _log_line(log_path: Path, rec: dict) -> None:
    line = json.dumps(rec, default=str)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


async def amain() -> int:
    args = parse_args()
    _load_env_and_weave()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "loop_log.jsonl"

    tasks = select_tasks(args)
    tasks_by_id = {t["id"]: t for t in tasks}
    complete = make_completer(args.model, temperature=args.temperature)
    mutator = make_completer(args.mutator_model or args.model, temperature=0.7)

    best_acc = -1.0
    best_overlay = _snapshot_overlay()
    iters = args.iters + 1  # iter 0 = baseline
    for it in range(iters):
        iter_dir = out_dir / f"iter{it}"
        t0 = time.time()
        summary, items = await run_iteration(
            complete,
            args.model,
            tasks,
            iter_dir,
            args.path,
            args.concurrency,
            weave_on(),
            f"tieout-loop-iter{it}",
        )
        acc = summary.get("cell_accuracy") or 0.0
        rec = {
            "iter": it,
            "cell_accuracy": acc,
            "pass_rate": summary.get("pass_rate"),
            "graded": summary.get("graded"),
            "missing": summary.get("missing"),
            "elapsed_s": round(time.time() - t0, 1),
            "overlay_skills": [e.get("name") for e in _snapshot_overlay()],
        }
        # Strictly-better keeps; ties keep the incumbent (simpler overlay).
        if acc > best_acc:
            if it > 0 and acc - best_acc > 0.10:
                rec["flag"] = "large-gain-audit"  # inspect before trusting
            best_acc = acc
            best_overlay = _snapshot_overlay()
            rec["decision"] = "baseline" if it == 0 else "kept"
        else:
            _write_overlay(best_overlay)
            rec["decision"] = "reverted" if it > 0 else "baseline"
        _log_line(log_path, rec)

        if it + 1 >= iters:
            break
        clusters = cluster_failures(items, tasks_by_id)
        if not clusters:
            _log_line(log_path, {"iter": it, "note": "no failures — nothing to fix"})
            break
        new_overlay, rationale = await propose_overlay(mutator, clusters, best_overlay)
        if not new_overlay:
            note = f"mutator stalled: {rationale}" if new_overlay is None else "mutator proposed no valid skills"
            _log_line(log_path, {"iter": it, "note": note})
            break
        _write_overlay(new_overlay)
        _log_line(log_path, {"iter": it, "mutation": rationale})

    _write_overlay(best_overlay)

    if args.holdout_dir:
        # Lockbox: scored once, after selection — never shown to the mutator.
        ho_tasks = load_dataset(args.holdout_dir)
        if args.holdout_sample:
            ho_tasks = ho_tasks[: args.holdout_sample]
        summary, _ = await run_iteration(
            complete,
            args.model,
            ho_tasks,
            out_dir / "holdout",
            args.path,
            args.concurrency,
            weave_on(),
            "tieout-holdout",
        )
        _log_line(log_path, {"holdout": summary})
        print(f"holdout: {json.dumps(summary)}")

    print(f"done. best cell_accuracy={best_acc} over {iters} iteration(s)")
    return 0


def select_tasks(args) -> list[dict]:
    tasks = load_dataset(args.dataset_dir)
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


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="tieout self-improvement loop")
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--ids", help="comma-separated task ids")
    p.add_argument("--ids-file", help="file with one task id per line")
    p.add_argument("--sample", type=int, default=20, help="first N tasks (default 20)")
    p.add_argument("--iters", type=int, default=3, help="improvement iterations after baseline")
    p.add_argument("--model", default="wandb:meta-llama/Llama-3.3-70B-Instruct")
    p.add_argument("--mutator-model", help="adapter spec for the mutator (default: --model)")
    p.add_argument("--path", default="hybrid")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--out-dir", default="/tmp/tieout-loop")
    p.add_argument("--holdout-dir", help="lockbox dataset scored once at the end")
    p.add_argument("--holdout-sample", type=int, help="first N holdout tasks")
    return p.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(amain()))
