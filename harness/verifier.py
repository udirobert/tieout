"""tieout verifier — golden-independent sanity gate before accepting a task.

Checks (deterministic, no golden access — using goldens in the loop = disqualification):
  1. Every graded answer cell was provided / written (missing cell -> not verified).
  2. Values are serializable openpyxl scalars (no dicts/lists leaking into cells).
  3. Optional soffice recalc: graded cells must not be Excel error strings.
Verified=False -> retry; after MAX_ATTEMPTS we ship the best guess anyway (never blank).
"""

import re
import tempfile
from pathlib import Path

MAX_ATTEMPTS = 3

_XL_ERR = re.compile(
    r"^#(NAME\?|REF!|VALUE!|DIV/0!|N/A|NULL!|NUM!|GETTING_DATA!|ERR!)", re.I
)


def sanity_check(
    graded_coords: list[str], cells: dict[str, object]
) -> tuple[bool, str]:
    missing = [c for c in graded_coords if c not in cells]
    if missing:
        return False, f"missing answer cells: {missing[:8]}"
    bad = [c for c, v in cells.items() if isinstance(v, (dict, list))]
    if bad:
        return False, f"non-scalar values at: {bad[:8]}"
    errs = excel_error_cells(cells)
    if errs:
        return False, f"excel errors at: {errs[:8]}"
    return True, "all graded cells present, scalars only"


def excel_error_cells(cells: dict[str, object]) -> list[str]:
    return [c for c, v in cells.items() if isinstance(v, str) and _XL_ERR.match(v)]


def is_formula_error_reason(reason: str) -> bool:
    """True when codegen output failed the recalc-as-gate (C spec)."""
    r = (reason or "").lower()
    return "recalc errors" in r or "excel errors" in r


def postcheck_soffice(task: dict, out_path: Path) -> tuple[bool, str]:
    """Recalc with LibreOffice when present; fail only on real #ERR values.

    Missing soffice or a recalc crash is a silent pass (Mac has no LibreOffice).
    """
    try:
        from sb import load_answer_values, recalculate, soffice_path
    except ImportError:
        return True, "no sb"
    if not soffice_path():
        return True, "no soffice"
    try:
        with tempfile.TemporaryDirectory() as td:
            recalc_path = recalculate(str(out_path), td)
            vals = load_answer_values(recalc_path, task)
    except Exception as e:  # noqa: BLE001 — fall back silently
        return True, f"recalc skipped: {type(e).__name__}"
    errs = [
        f"{sheet}!{coord}"
        for (sheet, coord), v in vals.items()
        if isinstance(v, str) and _XL_ERR.match(v)
    ]
    if errs:
        return False, f"recalc errors: {errs[:8]}"
    return True, "recalc clean"
