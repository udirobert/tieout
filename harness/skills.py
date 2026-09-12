"""tieout skills — category-specific prompt fragments & heuristics (Role C).

Guided by `harness/skills.py` categories and `research/methodology-notes.md`.
Reusable procedural guidance per task pattern (lookup repair, aggregation,
date arithmetic, sheet filtering, deduplication, fill-gating).

Self-improvement: `skills_overlay.json` (written by research/loop.py) adds or
replaces fragments at runtime. Entries: {"name", "keywords": [...], "text",
"replaces": "<BASE_SKILL_NAME>"?}. Empty keywords = always applied.
"""

import json
from pathlib import Path

LOOKUP_SKILL = (
    "### Domain Skill: Lookup & Index-Match\n"
    "- When resolving conditional lookups or days-since-event, trace values row-by-row.\n"
    "- Ensure exact cell reference alignment and handle missing/empty values with null."
)

AGGREGATION_SKILL = (
    "### Domain Skill: Multi-Criteria Aggregation\n"
    "- For time-of-day filtering, compare hours/minutes independently of the date component.\n"
    "- For multi-condition totals (SUMIFS/COUNTIFS logic), evaluate every condition conjunctively."
)

SHEET_REORG_SKILL = (
    "### Domain Skill: Sheet Filtering & VBA Equivalents\n"
    "- For row deletion or filtering rules, compute the exact surviving rows in original order.\n"
    "- When populating target ranges, do not leave gaps unless explicitly requested."
)

FILL_GATED_SKILL = (
    "### Domain Skill: Formatting-Gated Logic\n"
    "- The instruction specifies actions conditional on highlighted/colored cells.\n"
    "- Inspect the highlighted cell list carefully and apply the transform ONLY to matching coordinates."
)

DATE_TIME_SKILL = (
    "### Domain Skill: Date & Time Calculations\n"
    "- Return dates in standard ISO format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS).\n"
    "- Maintain exact day/month order and avoid locale-ambiguous formats."
)

RECONCILIATION_SKILL = (
    "### Domain Skill: Reconciliation Status\n"
    "- For each row, compare the key values (e.g., debits vs credits, net movement).\n"
    "- If the difference is within rounding tolerance (≈ 0.01), mark the row OK.\n"
    "- Otherwise mark EXCEPTION and stop — do not overwrite source columns."
)


def load_overlay() -> list[dict]:
    """Self-improvement overlay written by research/loop.py; [] when absent."""
    path = Path(__file__).with_name("skills_overlay.json")
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    entries = data.get("skills") if isinstance(data, dict) else data
    return [e for e in entries if isinstance(e, dict)] if entries else []


def get_skill_fragment(instruction: str) -> str:
    """Retrieve relevant domain skill fragments based on instruction text.

    Wired into the codegen *system* prompt (prompts.codegen_system) by category:
    lookup, aggregation, sheet-reorg, date, fill-gated. Keep fragments generic —
    the held-out private fund set punishes per-task hacks. Overlay fragments from
    skills_overlay.json append to (or replace, via "replaces") base fragments.
    """
    inst_lower = instruction.lower()
    overlay = load_overlay()
    replaced = {e.get("replaces") for e in overlay if e.get("replaces")}
    skills = []

    if "LOOKUP_SKILL" not in replaced and any(
        k in inst_lower
        for k in ("vlookup", "xlookup", "index", "match", "offset", "lookup")
    ):
        skills.append(LOOKUP_SKILL)
    if "AGGREGATION_SKILL" not in replaced and any(
        k in inst_lower
        for k in ("countif", "sumif", "averageif", "aggregate", "heatmap", "matrix")
    ):
        skills.append(AGGREGATION_SKILL)
    if "SHEET_REORG_SKILL" not in replaced and any(
        k in inst_lower
        for k in ("delete", "filter", "vba", "macro", "consolidat", "dedup", "merge")
    ):
        skills.append(SHEET_REORG_SKILL)
    if "FILL_GATED_SKILL" not in replaced and any(
        k in inst_lower
        for k in (
            "yellow",
            "highlight",
            "shad",
            "color",
            "colour",
            "cell fill",
            "fill color",
        )
    ):
        skills.append(FILL_GATED_SKILL)
    if "DATE_TIME_SKILL" not in replaced and any(
        k in inst_lower for k in ("date", "time", "day", "month", "year", "hour")
    ):
        skills.append(DATE_TIME_SKILL)
    if "RECONCILIATION_SKILL" not in replaced and any(
        k in inst_lower
        for k in ("reconcil", "exception", "status", "net movement", "debit", "credit")
    ):
        skills.append(RECONCILIATION_SKILL)

    for e in overlay:
        kws = [str(k).lower() for k in (e.get("keywords") or [])]
        if kws and not any(k in inst_lower for k in kws):
            continue
        text = (e.get("text") or "").strip()
        if text:
            skills.append(f"### Domain Skill: {e.get('name', 'Learned Skill')}\n{text}")

    return "\n\n".join(skills) if skills else ""
