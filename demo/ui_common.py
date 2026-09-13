"""Shared shell for the tieout marimo surfaces.

Every surface bootstraps the same paths, hunts for the same run artifacts, and
owes the reader the same statement of what is and is not verified. Keeping that
here is what stops a third surface becoming a fourth copy of the same preamble —
and stops a UI defaulting to a path that no longer exists, which is how
close_workspace.py came to open on an empty workspace.

Nothing here writes. The only write path a surface may use is
`exceptions.apply_decisions` (review decisions) and `memory_store` (governed
rules), both behind an explicit submit.
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Searched for run artifacts. Bounded on purpose: /tmp can hold anything, and a
# UI that walks the whole tree is slower than the demo it is meant to show.
_SEARCH_ROOTS = (Path("/tmp"), ROOT / "runs")
_MAX_DEPTH = 2

# The dirs the docs and demo scripts name. Floated above newer scratch so the
# console offers the run a reader was just told to produce.
_PREFERRED = (Path("/tmp/syndicate-demo"), Path("/tmp/tieout-loop"))

BOUNDARY = (
    "**Local pilot, not a product surface.** No authentication, reviewer identity "
    "is self-attested text, and nothing here posts to a ledger or writes back to a "
    "source workbook. Writes happen only on an explicit submit, through the same "
    "functions the CLI uses."
)


def bootstrap() -> None:
    """Put harness/, research/ and demo/ on sys.path. Idempotent."""
    for sub in ("harness", "research", "demo"):
        path = str(ROOT / sub)
        if path not in sys.path:
            sys.path.insert(0, path)


def _walk(root: Path, marker: str) -> list[Path]:
    """Dirs under `root`, to _MAX_DEPTH, that hold `marker`."""
    if not root.is_dir():
        return []
    found = []
    frontier = [root]
    for _ in range(_MAX_DEPTH):
        nxt = []
        for directory in frontier:
            try:
                entries = sorted(directory.iterdir())
            except OSError:
                continue
            for entry in entries:
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                if (entry / marker).exists():
                    found.append(entry)
                nxt.append(entry)
        frontier = nxt
    if (root / marker).exists():
        found.append(root)
    return found


def discover_runs() -> list[dict]:
    """Run dirs that actually hold artifacts, most recently touched first.

    Each entry reports what it has, so a surface can offer only the runs it can
    actually render instead of a path field the reader has to guess at.
    """
    seen: dict[Path, dict] = {}
    for root in _SEARCH_ROOTS:
        for marker in ("exceptions.json", "loop_log.jsonl"):
            for directory in _walk(root, marker):
                entry = seen.setdefault(
                    directory,
                    {
                        "path": directory,
                        "exceptions": False,
                        "loop_log": False,
                        "outputs": 0,
                        "traces": 0,
                        "tasks": [],
                        "mtime": 0.0,
                    },
                )
                if marker == "exceptions.json":
                    entry["exceptions"] = True
                else:
                    entry["loop_log"] = True
    for entry in seen.values():
        directory = entry["path"]
        entry["outputs"] = len(list((directory / "outputs").glob("*.xlsx")))
        entry["traces"] = (
            len(list((directory / "traces").rglob("*")))
            if (directory / "traces").is_dir()
            else 0
        )
        entry["tasks"] = _task_ids(directory)
        try:
            entry["mtime"] = directory.stat().st_mtime
        except OSError:
            pass
    return sorted(
        seen.values(), key=lambda e: (e["path"] not in _PREFERRED, -e["mtime"])
    )


def _task_ids(directory: Path) -> list[str]:
    path = directory / "exceptions.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    payloads = data if isinstance(data, list) else [data]
    return [str(p.get("task_id")) for p in payloads if p.get("task_id")]


def discover_memory_dbs() -> list[Path]:
    """Governed-memory SQLite files that exist, newest first."""
    found: set[Path] = set()
    for root in _SEARCH_ROOTS:
        for depth_glob in ("*/memory.sqlite3", "*/*/memory.sqlite3"):
            found.update(p for p in root.glob(depth_glob) if p.is_file())
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def memory_choices(limit: int = 10) -> dict[str, Path | str]:
    """Label -> governed-memory db for a dropdown, newest first.

    The not-found entry maps to "" rather than a plausible path: a picker that
    defaults to a directory that merely exists is how a surface ends up pointed at
    the wrong data.
    """
    found = discover_memory_dbs()
    if not found:
        return {"no memory.sqlite3 found — run demo/memory_scenario.py": ""}
    return {f"{p}  ({_age(p.stat().st_mtime)})": p for p in found[:limit]}


def discover_workbooks() -> list[Path]:
    """Transactions workbooks that sit beside a memory.sqlite3, newest first.

    Bounded to memory-scenario dirs on purpose. A run dir's `outputs/` hold graded
    answer workbooks: `memory_workbook.load_records` cannot read them, and offering
    them would let a reader import answer cells as if they were transactions.
    """
    found: list[Path] = []
    for db in discover_memory_dbs():
        found.extend(p for p in db.parent.glob("*.xlsx") if p.is_file())
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def workbook_choices(limit: int = 20) -> dict[str, Path | str]:
    """Label -> transactions workbook for a dropdown, newest first."""
    found = discover_workbooks()
    if not found:
        return {"no transactions workbook found — run demo/memory_scenario.py": ""}
    return {
        f"{p.parent.name}/{p.name}  ({_age(p.stat().st_mtime)})": p
        for p in found[:limit]
    }


def _age(mtime: float) -> str:
    """Compact relative age, so a picker of 30 run dirs is still readable."""
    if not mtime:
        return "unknown age"
    delta = max(0.0, time.time() - mtime)
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    return f"{int(delta // 86400)}d ago"


def describe_run(entry: dict) -> str:
    """One discovery entry as a dropdown label."""
    parts = [str(entry["path"]), _age(entry["mtime"])]
    if entry["tasks"]:
        parts.append(f"{len(entry['tasks'])} task(s)")
    if entry["exceptions"]:
        parts.append("exceptions")
    if entry["loop_log"]:
        parts.append("loop curve")
    if entry["outputs"]:
        parts.append(f"{entry['outputs']} workbook(s)")
    return " · ".join(parts)


def run_choices(limit: int = 15) -> dict[str, Path | str]:
    """Label -> path for a run dropdown, newest first, capped.

    A machine that has been used for experiments holds dozens of run dirs; showing
    all of them makes the picker unusable, so the rest are named in a final entry
    rather than silently dropped.
    """
    found = discover_runs()
    if not found:
        return {"no run artifacts found — run a demo first": ""}
    choices = {describe_run(e): e["path"] for e in found[:limit]}
    if len(found) > limit:
        choices[f"… {len(found) - limit} older run dir(s) not listed"] = found[limit][
            "path"
        ]
    return choices


def simulated(lineage_or_payload: dict) -> bool:
    """True when a run was written by demo/simulate_demo.sh rather than a model.

    The offline simulate path stamps `status='ok: simulated golden'`. Surfaces must
    say so: a 15/15 simulated run is construction, not evidence (docs/NEO4J.md).
    """
    status = str(lineage_or_payload.get("status") or "")
    return "simulated" in status.lower()
