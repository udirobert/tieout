"""Early-signal audit: codegen syntax/parse errors in a run's traces.

  python3 research/audit_lora_codegen_errors.py --run-dir /tmp/tinker-400-lora
  python3 research/audit_lora_codegen_errors.py --run-dir /tmp/tinker-400-codegen
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYNTAX = re.compile(
    r"syntax error|SyntaxError|invalid syntax|unexpected EOF|unterminated",
    re.I,
)
PARSE = re.compile(
    r"no JSON|JSONDecode|parse_code|no python|empty (code|script)|"
    r"did not write OUT_XLSX|disallowed (import|name)",
    re.I,
)


def _kind(task: dict) -> str:
    t = (task.get("instruction_type") or "").lower()
    return "sheet" if "sheet" in t else "cell"


def _load_kinds(dataset_dir: Path) -> dict[str, str]:
    tasks = json.loads((dataset_dir / "dataset.json").read_text())
    return {str(t["id"]): _kind(t) for t in tasks}


def _blob(trace: dict) -> str:
    parts = [str(trace.get("error") or "")]
    tout = trace.get("tool_output") or {}
    if isinstance(tout, dict):
        parts.append(str(tout.get("error") or ""))
        parts.append(str(tout.get("stderr") or ""))
    return "\n".join(parts)


def classify_trace(trace: dict) -> str | None:
    text = _blob(trace)
    if SYNTAX.search(text):
        return "syntax"
    if PARSE.search(text):
        return "parse_or_sandbox"
    if trace.get("tool") == "exec" and (trace.get("error") or (trace.get("tool_output") or {}).get("error")):
        return "exec_other"
    return None


def audit(run_dir: Path, kinds: dict[str, str]) -> dict:
    traces_dir = run_dir / "traces"
    files = sorted(traces_dir.glob("*.jsonl")) if traces_dir.exists() else []
    rows = []
    for path in files:
        tid = path.stem
        traces = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
        codegen = [t for t in traces if t.get("tool") == "exec" or "codegen" in str(t.get("error") or "").lower()]
        hits = []
        for t in traces:
            cat = classify_trace(t)
            if cat:
                hits.append(cat)
        rows.append(
            {
                "id": tid,
                "kind": kinds.get(tid, "?"),
                "n_traces": len(traces),
                "n_codegen": len(codegen),
                "hit": hits[0] if hits else None,
                "hits": hits,
            }
        )
    return {"n_files": len(files), "rows": rows}


def summarize(label: str, data: dict) -> None:
    rows = data["rows"]
    print(f"\n=== {label}  traces={data['n_files']} ===")
    if not rows:
        print("  (no traces yet)")
        return
    by_kind = {"sheet": [], "cell": [], "?": []}
    for r in rows:
        by_kind.setdefault(r["kind"], []).append(r)
    for kind in ("sheet", "cell", "?"):
        group = by_kind.get(kind) or []
        if not group:
            continue
        with_cg = [r for r in group if r["n_codegen"] or r["kind"] == "sheet"]
        syn = [r for r in group if r["hit"] == "syntax"]
        par = [r for r in group if r["hit"] == "parse_or_sandbox"]
        oth = [r for r in group if r["hit"] == "exec_other"]
        any_err = [r for r in group if r["hit"]]
        denom = len(group)
        print(
            f"  {kind:<6} n={denom:<4}  syntax={len(syn)} ({len(syn)/denom:.1%})  "
            f"parse/sandbox={len(par)} ({len(par)/denom:.1%})  "
            f"exec_other={len(oth)} ({len(oth)/denom:.1%})  "
            f"any_codegen_err={len(any_err)} ({len(any_err)/denom:.1%})"
        )
        if kind == "sheet" and syn:
            print(f"           syntax ids: {', '.join(r['id'] for r in syn[:20])}")
    c = Counter(r["hit"] for r in rows if r["hit"])
    print(f"  hit mix: {dict(c)}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", action="append", required=True)
    p.add_argument(
        "--dataset-dir",
        default=str(ROOT / "research/data/spreadsheetbench_verified_400"),
    )
    args = p.parse_args()
    dataset = Path(args.dataset_dir)
    if not dataset.exists():
        dataset = Path.home() / "tieout/research/data/spreadsheetbench_verified_400"
    kinds = _load_kinds(dataset)
    for run in args.run_dir:
        summarize(run, audit(Path(run), kinds))


if __name__ == "__main__":
    main()
