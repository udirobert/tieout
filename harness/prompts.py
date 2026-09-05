"""tieout prompts — task-typed, values-first v0, formulas v1.

Hybrid principle: reason hard tasks, direct easy ones.
Baseline system (upstream common.py) computes FINAL VALUES for the answer range.
v1 adds formula writing with _xlfn. prefix where scorer recalcs via LibreOffice.
"""

SYSTEM_VALUES = (
    "You are a spreadsheet expert. You get a serialized workbook and a user instruction. "
    "Compute the final values the answer range must contain after the instruction is applied. "
    "Return one entry per cell in the answer range. Use null for cells that must be empty. "
    "Return plain values, not formulas."
)

FORMAT_HINT = (
    "\n\nReply with JSON only, no prose, in this shape: "
    '{"cells": [{"cell": "B6", "value": 42}, {"cell": "B7", "value": null}]}'
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
    "No torch, no network, no pip install. Read the init workbook, compute the answer, "
    "write ONLY the graded answer cells, save to the output path. "
    'Print exactly one line: SUMMARY_JSON={"status": "ok|error", "notes": "..."}. '
    "Never fabricate numbers — compute them from the workbook."
)

VERIFY_PROMPT = (
    "Re-derive the answer a second way (e.g. pandas vs formula, or re-read written cells). "
    "If the two derivations disagree, say DISAGREE and explain. Otherwise say AGREE."
)


def classify(task: dict) -> str:
    """cell vs sheet + hint for prompt choice. Mirrors dataset instruction_type."""
    t = (task.get("instruction_type") or "").lower()
    if "sheet" in t:
        return "sheet-level"
    return "cell-level"


def build_values_prompt(task: dict, workbook_text: str) -> str:
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        f"## Workbook\n{workbook_text}\n\n"
        f"## Answer range\nSheet: {task.get('answer_sheet') or 'active sheet'}\n"
        f"Cells: {task['answer_position']}\n" + FORMAT_HINT
    )


# Attribution-guided repair (methodology-notes §2/§3: the documented biggest lever —
# targeted "what failed, why, smallest edit" instead of blind full retries).
# The previous reply is enough context for repair (it holds the full proposed answer);
# re-sending the workbook would double input tokens without fixing attribution.
def build_repair_prompt(
    task: dict, previous_reply: str, failure_reason: str, graded_cells: list[str]
) -> str:
    return (
        f"## Instruction\n{task['instruction']}\n\n"
        f"## Answer range\nSheet: {task.get('answer_sheet') or 'active sheet'}\n"
        f"Cells: {', '.join(graded_cells)}\n\n"
        f"## Your previous reply (rejected)\n{previous_reply[:8000]}\n\n"
        f"## What failed\n{failure_reason}\n\n"
        "Fix the smallest possible thing: keep every cell/value that is correct, change "
        "only what the failure describes. Return the complete corrected answer — one "
        "entry per cell in the answer range (unchanged cells included), null for cells "
        "that must be empty, plain values not formulas." + FORMAT_HINT
    )
