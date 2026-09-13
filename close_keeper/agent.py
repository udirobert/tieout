"""close-keeper — a Strands Agents SDK agent for the financial close.

Built on tieout's machinery, exposed as tools:

- tie out workbooks through the tieout pipeline (harness/pipeline.py)
- list the exceptions that genuinely need a human decision
- write review decisions ONLY through the recorded path (exceptions.apply_decisions)
- resolve mappings against governed business memory, and route every learned
  correction through governance: record -> propose -> validate -> activate

The agent runs quietly in the background and surfaces only real decisions —
that is the design brief, not a feature toggle.

    research/.venv/bin/python -m close_keeper "tie out this week's close"

Model: any OpenAI-compatible endpoint via CLOSE_KEEPER_BASE_URL /
CLOSE_KEEPER_API_KEY / CLOSE_KEEPER_MODEL (falls back to OPENAI_BASE_URL /
OPENAI_API_KEY). With AWS credentials present, Strands' default Bedrock model
works too — pass --bedrock.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "research" / "baseline"))

from strands import Agent, tool  # noqa: E402

RESEARCH_PYTHON = ROOT / "research" / ".venv" / "bin" / "python"

DEFAULT_DATASET_DIR = ROOT / "demo" / "close-tieout"
DEFAULT_OUT_DIR = Path("/tmp/close-keeper-run")


def load_env() -> None:
    """Same loader as harness/pipeline.py: repo .env then research/.env, setdefault."""
    for env_path in (ROOT / ".env", ROOT / "research" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _run_env() -> dict:
    """Child-process env: current environment plus .env keys (never echoed)."""
    load_env()
    return dict(os.environ)


# ---------------------------------------------------------------- tools


@tool
def tie_out_workbook(dataset_dir: str, out_dir: str, ids: str = "") -> str:
    """Tie out a close workbook: run the tieout pipeline over the task(s).

    The pipeline classifies each answer range, generates values or sheet code,
    verifies the result, repairs up to three times, and leaves cells blank when
    no answer clears the gate — blank means "route to a human", never a guess.
    After the run, every flagged cell lands in the exception queue.

    Args:
        dataset_dir: directory with dataset.json + spreadsheets (the close package)
        out_dir: run directory for predictions.jsonl, outputs/, traces/, exceptions.json
        ids: optional comma-separated task ids (default: every task in the package)
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(RESEARCH_PYTHON) if RESEARCH_PYTHON.exists() else sys.executable,
        str(ROOT / "harness" / "pipeline.py"),
        "--dataset-dir", dataset_dir,
        "--out-dir", str(out),
        "--path", "hybrid",
    ]
    if ids.strip():
        cmd += ["--ids", ids.strip()]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=1800, env=_run_env()
    )
    tail = "\n".join((proc.stdout or "").splitlines()[-15:])
    err_tail = "\n".join((proc.stderr or "").splitlines()[-8:])
    exc = out / "exceptions.json"
    n_exc = 0
    if exc.exists():
        try:
            payloads = json.loads(exc.read_text())
            n_exc = sum(len(p.get("exceptions", [])) for p in payloads)
        except Exception:  # noqa: BLE001
            pass
    return (
        f"pipeline exit {proc.returncode}; exceptions queued: {n_exc}\n"
        f"--- output tail ---\n{tail}"
        + (f"\n--- stderr tail ---\n{err_tail}" if proc.returncode != 0 else "")
    )


@tool
def list_exceptions(out_dir: str) -> str:
    """List the cells waiting on a human decision after a tie-out run.

    Each entry carries the cell, why it was flagged, the value the agent
    proposed (if any), and source-row evidence. These are the ONLY items the
    human should be disturbed with; everything else was filed autonomously.
    """
    path = Path(out_dir) / "exceptions.json"
    if not path.exists():
        return "no exceptions.json — run tie_out_workbook first"
    payloads = json.loads(path.read_text())
    lines: list[str] = []
    for payload in payloads:
        pending = [e for e in payload.get("exceptions", []) if e.get("status") == "pending"]
        if not pending:
            continue
        lines.append(f"task {payload['task_id']}: {len(pending)} pending")
        for exc in pending:
            ev = exc.get("evidence_rows", [])[:2]
            ev_s = "; ".join(f"{e['sheet']} row {e['row']} (key={e['key']})" for e in ev)
            lines.append(
                f"  {exc['cell']} | {exc['reason']} | proposed: {exc.get('proposed_value')!r}"
                + (f" | evidence: {ev_s}" if ev_s else "")
            )
    return "\n".join(lines) if lines else "no pending exceptions — the run is fully filed"


@tool
def apply_review_decisions(out_dir: str, decisions: dict) -> str:
    """Apply human review decisions to the exception queue — the one write path.

    Approved cells keep the proposed value; rejected and undecided cells revert
    to the init value. Decisions are persisted before any workbook is touched,
    so an approval is never lost and a value is never written without a
    recorded decision.

    Args:
        out_dir: run directory holding exceptions.json
        decisions: {task_id: {"Sheet!CELL": "approved" | "rejected"}}
    """
    import exceptions as exc_mod  # harness/exceptions.py

    path = Path(out_dir) / "exceptions.json"
    if not path.exists():
        return "no exceptions.json — nothing to decide"
    payloads, as_array = exc_mod.load_exceptions(path)
    clean: dict[str, dict[str, str]] = {}
    for task_id, cells in (decisions or {}).items():
        clean[task_id] = {}
        for cell, verdict in (cells or {}).items():
            verdict = str(verdict).strip().lower()
            if verdict not in ("approved", "rejected"):
                return f"invalid verdict for {task_id} {cell}: {verdict!r} (approved|rejected)"
            clean[task_id][cell] = verdict
    for payload in payloads:
        for exc in payload.get("exceptions", []):
            verdict = clean.get(payload["task_id"], {}).get(exc["cell"])
            if verdict:
                exc["status"] = verdict
    exc_mod.apply_decisions(payloads, clean, path, as_array=as_array)
    n = sum(len(c) for c in clean.values())
    return f"applied {n} decision(s); workbooks rewritten with approved values only"


# ---------------------------------------------------- governed memory


def _store(memory_db: str):
    from memory_store import MemoryStore  # harness/memory_store.py

    path = Path(memory_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    return MemoryStore(path)


@tool
def list_memory_rules(memory_db: str) -> str:
    """List business rules in governed memory with their lifecycle status.

    candidate -> validated -> active, or revoked. Only ACTIVE rules ever
    influence a mapping; candidates and revoked rules are inert history.
    """
    with _store(memory_db) as store:
        rules = store.rules()
    if not rules:
        return "memory is empty — no rules yet"
    lines = [
        f"{r['rule']['rule_id'][:8]} | {r['status']:9} | {r['rule']['alias'][:60]} -> {r['rule']['vendor']}"
        for r in rules
    ]
    return "\n".join(lines)


@tool
def suggest_mappings(memory_db: str, records: list[dict]) -> str:
    """Resolve records against ACTIVE memory rules (read-only).

    Each record needs record_id, scope {tenant, entity, account, currency},
    narrative, optional vendor_hint, and source {workbook_sha256, sheet, cell}.
    Returns 'suggested' only on an exact approved alias match; anything else
    comes back 'review' — the agent must not fill those in.
    """
    with _store(memory_db) as store:
        out = store.suggest(records)
    return json.dumps(out, indent=2, default=str)


@tool
def record_correction(memory_db: str, record: dict, vendor: str, reviewer: str, rationale: str) -> str:
    """Record a human-taught correction in governed memory (step 1 of 4).

    A correction is evidence, not a rule: it influences nothing until it is
    proposed, validated against labeled replay cases, and activated. Reviewer
    names are self-attested.
    """
    with _store(memory_db) as store:
        correction = store.record_correction(record, vendor, reviewer, rationale)
    return json.dumps(correction, indent=2, default=str)


@tool
def propose_rule(memory_db: str, correction_id: str) -> str:
    """Turn a recorded correction into a candidate rule (step 2 of 4)."""
    with _store(memory_db) as store:
        rule = store.propose(correction_id)
    return json.dumps(rule, indent=2, default=str)


@tool
def validate_rule(memory_db: str, rule_id: str, cases: list[dict], reviewer: str) -> str:
    """Replay a candidate rule against labeled cases (step 3 of 4).

    The gate requires positive, hard-negative, scope-boundary and conflict
    coverage with zero regressions; the replay must not reuse the correction
    workbook. A rule that fails stays inactive — report the failure, do not
    retry with weaker cases.
    """
    with _store(memory_db) as store:
        report = store.validate(rule_id, cases, reviewer)
    return json.dumps(report, indent=2, default=str)


@tool
def activate_rule(memory_db: str, rule_id: str, reviewer: str) -> str:
    """Activate a validated rule (step 4 of 4). Refused unless validation passed."""
    with _store(memory_db) as store:
        event = store.activate(rule_id, reviewer)
    return json.dumps(event, indent=2, default=str)


@tool
def revoke_rule(memory_db: str, rule_id: str, reviewer: str, reason: str) -> str:
    """Revoke an active rule with a recorded reason (e.g. it misfired in production)."""
    with _store(memory_db) as store:
        event = store.revoke(rule_id, reviewer, reason)
    return json.dumps(event, indent=2, default=str)


@tool
def preview_workbook(path: str, max_rows: int = 40, max_cols: int = 12) -> str:
    """Read a text preview of a workbook (values only) to ground a decision."""
    from sb import serialize_workbook  # research/sb.py

    return serialize_workbook(path, max_rows=max_rows, max_cols=max_cols)


TOOLS = [
    tie_out_workbook,
    list_exceptions,
    apply_review_decisions,
    list_memory_rules,
    suggest_mappings,
    record_correction,
    propose_rule,
    validate_rule,
    activate_rule,
    revoke_rule,
    preview_workbook,
]


# ---------------------------------------------------------------- agent

SYSTEM_PROMPT = """You are close-keeper, an agent for finance professionals during the financial close.

You run quietly in the background. You tie out close workbooks, file every answer
you can verify, and resolve mapping questions against approved business memory.
You surface ONLY genuine decisions — the flagged cells where judgment is required.

Your working agreement:
- Blank is an answer. If the pipeline or memory cannot verify a value, it routes
  to the exception queue. You never fill a cell on a hunch.
- You write approved values ONLY through apply_review_decisions, after the human
  has decided. There is no other write path and you do not improvise one.
- Memory learns only through governance: record_correction -> propose_rule ->
  validate_rule -> activate_rule. If validation fails, the rule stays inactive
  and you say so. You never weaken replay cases to force a pass.
- When you surface exceptions, be brief: cell, why flagged, proposed value,
  evidence. The human's attention is the scarcest resource in the close.

Workspace for this session:
- close package (dataset): {dataset_dir}
- run directory: {out_dir}
- governed memory db: {memory_db}
"""


def make_model(use_bedrock: bool):
    """Resolve the agent-loop model. None means Strands' default (Bedrock)."""
    load_env()
    if use_bedrock:
        return None
    from strands.models.openai import OpenAIModel

    if os.environ.get("CLOSE_KEEPER_API_KEY"):
        base_url = os.environ.get("CLOSE_KEEPER_BASE_URL")
        api_key = os.environ["CLOSE_KEEPER_API_KEY"]
        model_id = os.environ.get("CLOSE_KEEPER_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    elif os.environ.get("WANDB_API_KEY"):
        # the repo's funded path: W&B Serverless Inference (OpenAI-compatible)
        base_url = "https://api.inference.wandb.ai/v1"
        api_key = os.environ["WANDB_API_KEY"]
        model_id = os.environ.get("CLOSE_KEEPER_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    else:
        base_url = os.environ.get("OPENAI_BASE_URL")
        api_key = os.environ.get("OPENAI_API_KEY")
        model_id = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        raise SystemExit(
            "no API key: set CLOSE_KEEPER_API_KEY or WANDB_API_KEY, or pass --bedrock"
        )
    return OpenAIModel(
        client_args={"api_key": api_key, **({"base_url": base_url} if base_url else {})},
        model_id=model_id,
    )


def make_agent(model, dataset_dir: str, out_dir: str, memory_db: str) -> Agent:
    return Agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT.format(
            dataset_dir=dataset_dir, out_dir=out_dir, memory_db=memory_db
        ),
    )


def build_agent(args: argparse.Namespace) -> Agent:
    return make_agent(make_model(args.bedrock), args.dataset_dir, args.out_dir, args.memory_db)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("prompt", help="what you want close-keeper to do")
    p.add_argument("--dataset-dir", default=str(DEFAULT_DATASET_DIR))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--memory-db", default=str(DEFAULT_OUT_DIR / "memory.sqlite3"))
    p.add_argument("--bedrock", action="store_true", help="use Strands' default Bedrock model")
    args = p.parse_args()
    agent = build_agent(args)
    print(agent(args.prompt))


if __name__ == "__main__":
    main()
