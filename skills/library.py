"""C-owned skill fragments. A calls fragment_for(task) from harness/prompts.py.

Return a short reusable prompt fragment for the task category, or "".
Generic patterns only — the held-out private fund set punishes overfit.

Retrieval plan (docs/RESULTS_CHECKLIST.md §Ablation):
- Category is detected from the instruction text + instruction_type keywords
  (no task-id matching, no dataset-specific cells/sheet names).
- Multiple categories may fire; fragments are joined, capped, and kept short
  (< ~400 chars) so they shift behavior without crowding out the workbook.
- Ablation matrix planned: {values, codegen} x {no-skill, skill} on a fixed
  40-task stratified subset (10 per category), then full-400 if positive.
"""

MAX_FRAGMENTS = 2

# ---------------------------------------------------------------- fragments

LOOKUP_REBUILD = (
    "### Skill: lookup rebuild\n"
    "- Build the lookup in code: load the key->value columns into a dict, then map each "
    "target cell. Do not copy a broken VLOOKUP/INDEX formula verbatim.\n"
    "- Match keys exactly as stored (strip whitespace, cast numeric-looking IDs to string "
    "consistently on both sides). Unmatched keys: leave the cell empty rather than guessing."
)

AGGREGATION_PIVOT = (
    "### Skill: aggregation / pivot\n"
    "- Group rows with a dict keyed by the condition columns, then aggregate with sum/count/"
    "min/max as instructed. Every condition must hold (AND), including date or time windows.\n"
    "- When comparing times of day, compare hour/minute only if the date component is "
    "irrelevant. Write one output value per expected output cell, in order."
)

DATE_ARITHMETIC = (
    "### Skill: date arithmetic\n"
    "- Parse dates with datetime (try common formats); keep them as datetime objects, "
    "never strings, until the final write.\n"
    "- Day differences are (a - b).days on dates; respect inclusive/exclusive wording in the "
    "instruction. Output dates as YYYY-MM-DD (or YYYY-MM-DD HH:MM:SS if times are involved)."
)

SHEET_REORG = (
    "### Skill: sheet reorganization\n"
    "- Never run/emit VBA or macros; implement the equivalent Python transform on the sheets.\n"
    "- When deleting rows, iterate bottom-up so indices stay valid; preserve the header row "
    "and any rows above it unless told otherwise.\n"
    "- Keep sheet names byte-exact (quotes/spaces matter). Do not create helper sheets or "
    "write outside the requested target range."
)

FILL_GATED = (
    "### Skill: formatting-gated logic\n"
    "- The instruction gates on cell appearance (highlight/fill/color). Read each cell's "
    "fill color (openpyxl `cell.fill.start_color.rgb`) and apply the transform ONLY to "
    "cells whose fill matches the stated color."
)

SERIALIZATION_GUARD = (
    "### Skill: writing cells\n"
    "- Write computed VALUES (not formulas) unless the task explicitly requires formula text.\n"
    "- Write every requested answer cell; an unwritten cell scores zero. Convert Python "
    "types to plain scalars (no numpy types, no datetime objects — use ISO strings)."
)

_CATEGORIES = (
    # (name, fragment, keywords on lowercased instruction)
    ("lookup", LOOKUP_REBUILD,
     ("vlookup", "xlookup", "index(", "match(", "offset(", "hlookup", "lookup", "replace.*id",
      "corresponding names")),
    ("aggregation", AGGREGATION_PIVOT,
     ("countif", "sumif", "averageif", "pivot", "aggregate", "heatmap", "heat map",
      "matrix", "group by", "subtotal")),
    ("date", DATE_ARITHMETIC,
     ("date", "day", "month", "year", "week", "days since", "timestamp", "ageing", "aging")),
    ("sheet_reorg", SHEET_REORG,
     ("delete", "filter", "vba", "macro", "sort", "dedup", "duplicate", "consolidat",
      "merge", "combine", "reorganiz", "reorganis", "remove", "move rows")),
    ("fill_gated", FILL_GATED,
     ("yellow", "highlight", "shad", "colored", "coloured", "color fill", "fill color")),
    ("serialization", SERIALIZATION_GUARD,
     ()),
)


def _keyword_hit(lowered: str, keywords) -> bool:
    for k in keywords:
        if k in lowered:
            return True
    return False


def categorize(task: dict) -> list:
    """Return category names for a task, most-specific first. Generic keyword rules."""
    text = (task.get("instruction") or task.get("prompt") or "").lower()
    hits = [name for name, _frag, kws in _CATEGORIES if kws and _keyword_hit(text, kws)]
    return hits


def fragment_for(task: dict) -> str:
    """Prompt fragment for the task (joined categories, capped, generic only)."""
    hits = categorize(task)
    # serialization guard always applies — unwritten/mistyped cells were a top failure
    frags = [frag for name, frag, _ in _CATEGORIES
             if name in hits or name == "serialization"][:MAX_FRAGMENTS]
    return "\n\n".join(frags).strip()

