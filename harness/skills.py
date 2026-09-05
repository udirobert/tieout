"""tieout skills — category-specific prompt fragments & heuristics (Role C).

Guided by docs/TAXONOMY.md and research/methodology-notes.md (§4.4).
Reusable procedural guidance per task pattern (lookup repair, aggregation,
date arithmetic, sheet filtering, deduplication, fill-gating).
"""

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


def get_skill_fragment(instruction: str) -> str:
    """Retrieve relevant domain skill fragments based on instruction text.

    Wired into the codegen *system* prompt (prompts.codegen_system) by category:
    lookup, aggregation, sheet-reorg, date, fill-gated. Keep fragments generic —
    the held-out private fund set punishes per-task hacks.
    """
    inst_lower = instruction.lower()
    skills = []

    if any(k in inst_lower for k in ("vlookup", "xlookup", "index", "match", "offset", "lookup")):
        skills.append(LOOKUP_SKILL)
    if any(k in inst_lower for k in ("countif", "sumif", "averageif", "aggregate", "heatmap", "matrix")):
        skills.append(AGGREGATION_SKILL)
    if any(k in inst_lower for k in ("delete", "filter", "vba", "macro", "consolidat", "dedup", "merge")):
        skills.append(SHEET_REORG_SKILL)
    if any(k in inst_lower for k in ("yellow", "highlight", "shad", "color", "colour", "fill")):
        skills.append(FILL_GATED_SKILL)
    if any(k in inst_lower for k in ("date", "time", "day", "month", "year", "hour")):
        skills.append(DATE_TIME_SKILL)

    return "\n\n".join(skills) if skills else ""
