"""tieout executor — runs model-written openpyxl code in a subprocess sandbox.

Copies the init workbook into a temp dir so the script never sees the dataset
folder (goldens live next to init; reading them is a disqualification).
Timeout, stdout/stderr tail cap, import allowlist, API keys stripped from env.
"""

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_S = 120
STDOUT_CAP = 4000
ALLOWED_IMPORTS = frozenset(
    {
        "openpyxl",
        "datetime",
        "math",
        "json",
        "re",
        "statistics",
        "collections",
        "itertools",
        "copy",
        "decimal",
        "string",
        "functools",
        "operator",
        "heapq",
        "bisect",
        "numbers",
        "typing",
    }
)
_BANNED_NAMES = frozenset(
    {"eval", "exec", "compile", "__import__", "open", "breakpoint"}
)
_SECRET_NAMES = frozenset(
    {
        "TINKER_API_KEY",
        "GEMINI_API_KEY",
        "PARALLEL_API_KEY",
        "OPENROUTER_API_KEY",
        "FASTINO_API_KEY",
        "PIONEER_API_KEY",
        "TINKER_PROJECT_ID",
    }
)


def _tail(text: str, n: int = STDOUT_CAP) -> str:
    return text if len(text) <= n else text[-n:]


def _check_code(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"syntax error: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in ALLOWED_IMPORTS:
                    return f"disallowed import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top not in ALLOWED_IMPORTS:
                return f"disallowed import: {node.module}"
        elif isinstance(node, ast.Name) and node.id in _BANNED_NAMES:
            return f"disallowed name: {node.id}"
        elif isinstance(node, ast.Attribute) and node.attr in _BANNED_NAMES:
            return f"disallowed name: {node.attr}"
    return None


def _summary(stdout: str) -> dict | None:
    for line in reversed(stdout.splitlines()):
        if "SUMMARY_JSON=" in line:
            raw = line.split("SUMMARY_JSON=", 1)[1].strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
    return None


def _sandbox_env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in _SECRET_NAMES and not k.endswith(("_API_KEY", "_TOKEN", "_SECRET"))
    }
    return env


def run_snippet(code: str, init_xlsx: str, out_xlsx: str) -> dict:
    """Run model-written snippet. Returns {ok, stdout, stderr, error, summary}.

    INIT_XLSX / OUT_XLSX are injected as string literals. The real dataset path
    never enters the sandbox, so golden files are not reachable.
    """
    blocked = _check_code(code)
    if blocked:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": blocked,
            "summary": None,
        }

    Path(out_xlsx).parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tieout-exec-") as td:
        td_path = Path(td)
        local_init = td_path / "init.xlsx"
        local_out = td_path / "out.xlsx"
        shutil.copy(init_xlsx, local_init)
        preamble = f"INIT_XLSX = {str(local_init)!r}\nOUT_XLSX = {str(local_out)!r}\n"
        script = td_path / "snippet.py"
        script.write_text(preamble + "\n" + code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                cwd=td,
                env=_sandbox_env(),
            )
        except subprocess.TimeoutExpired as e:
            stdout = _tail(e.stdout or "")
            stderr = _tail(e.stderr or "")
            return {
                "ok": False,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"timeout after {TIMEOUT_S}s",
                "summary": _summary(stdout),
            }
        stdout = _tail(proc.stdout or "")
        stderr = _tail(proc.stderr or "")
        summary = _summary(stdout)
        if local_out.exists():
            shutil.copy(local_out, out_xlsx)
        # Valid SUMMARY_JSON + an output file counts even if the process
        # crashed afterwards (evidence produced is what matters).
        wrote = local_out.exists()
        ok = wrote and (
            proc.returncode == 0
            or (summary is not None and summary.get("status") == "ok")
        )
        error = None
        if not ok:
            if not wrote:
                error = "script did not write OUT_XLSX"
            elif proc.returncode != 0:
                error = f"exit {proc.returncode}: {stderr or stdout or 'no output'}"[
                    :300
                ]
            else:
                error = "script failed"
        return {
            "ok": ok,
            "stdout": stdout,
            "stderr": stderr,
            "error": error,
            "summary": summary,
        }
