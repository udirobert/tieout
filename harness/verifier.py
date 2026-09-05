"""tieout verifier — golden-independent sanity gate before accepting a task.

Checks (deterministic, no golden access — using goldens in the loop = disqualification):
  1. Every graded answer cell was provided by the model (missing cell -> not verified).
  2. Values are serializable openpyxl scalars (no dicts/lists leaking into cells).
Verified=False -> retry; after MAX_ATTEMPTS we ship the best guess anyway (never blank).
"""

MAX_ATTEMPTS = 3


def sanity_check(
    graded_coords: list[str], cells: dict[str, object]
) -> tuple[bool, str]:
    missing = [c for c in graded_coords if c not in cells]
    if missing:
        return False, f"missing answer cells: {missing[:8]}"
    bad = [c for c, v in cells.items() if isinstance(v, (dict, list))]
    if bad:
        return False, f"non-scalar values at: {bad[:8]}"
    return True, "all graded cells present, scalars only"
