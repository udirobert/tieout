"""tieout prompts — values-first + codegen, attribution-guided repair.

Sheet-level (and cell-level after values-first exhaustion) use CODEGEN_SYSTEM.
Values-first stays the always-works fallback. Thinking stays off (adapters).
Optional skill fragments: C owns repo-root `skills/library.py` (`fragment_for`).
"""

import sys
from pathlib import Path

SYSTEM_VALUES = (
    "You are a spreadsheet expert. You get a serialized workbook and a user instruction. "
    "Compute the final values the answer range must contain after the instruction is applied. "
    "Return one entry per cell in the answer range. Use null for cells that must be empty. "
    "Return plain values, not formulas."
)

FORMAT_HINT = (
    "\n\nReply with JSON only, no prose, in this shape: "
    '{"cells": [{"cell": "B6", "value": 42}, {"cell": "Sheet2!A1", "value": null}]} '
    "Use Sheet!A1 when the answer spans more than one sheet."
)

# v1: when the instruction asks for a formula, write the formula string instead.
# Newer Excel functions need the stored prefix or LibreOffice + Excel return #NAME?:
#   _xlfn.XLOOKUP, _xlfn.UNIQUE, _xlfn.LET, _xlfn.CHOOSECOLS, _xlfn._xlws.FILTER
# Classic SUM/SUMIFS/INDEX/MATCH/VLOOKUP need no prefix. Dates as real dates, not text.
SYSTEM_FORMULA = (
    "You are a spreadsheet expert. You get a serialized workbook and a user instruction. "
    "Return the formula string each answer cell must contain (with _xlfn. prefix for "
    "XLOOKUP/UNIQUE/LET/CHOOSECOLS/FILTER). If the task wants values, return values. "
    'Reply with JSON only: {"cells": [{"cell": "B6", "value": "=SUM(A1:A5)"}]}'
)

CODEGEN_SYSTEM = (
    "You write self-contained Python that edits a workbook with openpyxl ONLY. "
    "No torch, no network, no pip install, no os/sys/subprocess/pathlib. "
    "INIT_XLSX and OUT_XLSX are already defined as path strings. "
    "Load INIT_XLSX, compute the answer from the real workbook (not the preview), "
    "write the graded answer cells, save to OUT_XLSX. "
    'Print exactly one line: SUMMARY_JSON={"status": "ok|error", "notes": "..."}. '
    "Never fabricate numbers — compute them from the workbook. "
    "Allowed imports: openpyxl, datetime, math, json, re, statistics, collections, "
    "itertools, copy, decimal."
)

CODEGEN_FORMAT = (
    "\n\nReply with a single Python script in a ```python fence. No prose. "
    "INIT_XLSX and OUT_XLSX are predefined. Save OUT_XLSX and print one SUMMARY_JSON line."
)


def _skill_fragment(task: dict) -> str:
    """C-owned hook. Empty until skills/library.py exists. Never import harness/."""
    root = Path(__file__).resolve().parent.parent / "skills"
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from library import fragment_for  # type: ignore
    except ImportError:
        return ""
    try:
        text = (fragment_for(task) or "").strip()
    except Exception:
        return ""
    return f"\n\n## Skill\n{text}\n" if text else ""


def classify(task: dict) -> str:
    """cell vs sheet + hint for prompt choice. Mirrors dataset instruction_type."""
    t = (task.get("instruction_type") or "").lower()
    if "sheet" in t:
        return "sheet-level"
    return "cell-level"


def _range_block(task: dict) -> str:
    data = task.get("data_position")
    extra = f"Data range: {data}\n" if data else ""
    return (
        f"## Answer range\nSheet: {task.get('answer_sheet') or 'active sheet'}\n"
        f"Cells: {task['answer_position']}\n{extra}"
    )


def build_values_prompt(task: dict, workbook_text: str) -> str:
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        f"## Workbook\n{workbook_text}\n\n"
        + _range_block(task)
        + _skill_fragment(task)
        + FORMAT_HINT
    )


def build_repair_prompt(
    task: dict,
    previous_reply: str,
    failure_reason: str,
    graded_cells: list[str],
    workbook_text: str = "",
) -> str:
    wb_section = f"## Workbook\n{workbook_text}\n\n" if workbook_text else ""
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        + wb_section
        + f"## Answer range\nSheet: {task.get('answer_sheet') or 'active sheet'}\n"
        f"Cells: {', '.join(graded_cells)}\n\n"
        f"## Your previous reply (rejected)\n{previous_reply[:8000]}\n\n"
        f"## What failed\n{failure_reason}\n\n"
        "Fix the smallest possible thing: keep every cell/value that is correct, change "
        "only what the failure describes. Return the complete corrected answer — one "
        "entry per cell in the answer range (unchanged cells included), null for cells "
        "that must be empty, plain values not formulas. Use Sheet!A1 when the answer "
        "spans more than one sheet." + FORMAT_HINT
    )


def build_codegen_prompt(
    task: dict, workbook_text: str, graded_cells: list[str]
) -> str:
    shown = ", ".join(graded_cells[:80])
    more = " ..." if len(graded_cells) > 80 else ""
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        f"## Workbook (preview — read INIT_XLSX for full data)\n{workbook_text}\n\n"
        + _range_block(task)
        + f"Graded cells: {shown}{more}\n"
        + _skill_fragment(task)
        + CODEGEN_FORMAT
    )


def build_codegen_repair_prompt(
    task: dict,
    previous_code: str,
    failure_reason: str,
    stdout: str,
    stderr: str,
    graded_cells: list[str],
) -> str:
    shown = ", ".join(graded_cells[:80])
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        f"## Answer range\nSheet: {task.get('answer_sheet') or 'active sheet'}\n"
        f"Cells: {task['answer_position']}\n"
        f"Graded cells: {shown}\n\n"
        f"## Your previous script (rejected)\n```python\n{previous_code[:8000]}\n```\n\n"
        f"## What failed\n{failure_reason}\n\n"
        f"## stdout (tail)\n{stdout[-1500:]}\n\n"
        f"## stderr (tail)\n{stderr[-1500:]}\n\n"
        "Fix the smallest possible thing. INIT_XLSX and OUT_XLSX are still predefined. "
        "Return a complete corrected script." + CODEGEN_FORMAT
    )
