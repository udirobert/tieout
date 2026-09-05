"""tieout serializer — upstream serialization + fill-aware enrichment.

Formatting-gated tasks (docs/TAXONOMY.md #4) need cell.fill: plain serialization
drops it. When the instruction mentions highlighting/color, append the highlighted
cells per sheet. Values capped at MAX_WORKBOOK_CHARS with an explicit truncation note.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))

from sb import serialize_workbook  # noqa: E402

MAX_WORKBOOK_CHARS = 20000

_FILL_TRIGGER = re.compile(r"yellow|highlight|shad|fill colou?r|colou?r.*fill", re.I)


def _fill_lines(path: str, max_rows=120, max_cols=30) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(path)
    out = []
    for ws in wb.worksheets:
        hits = []
        for row in ws.iter_rows(
            min_row=1,
            max_row=min(ws.max_row, max_rows),
            max_col=min(ws.max_column, max_cols),
        ):
            for cell in row:
                fg = (
                    getattr(cell.fill, "fgColor", None)
                    if cell.fill and cell.fill.patternType
                    else None
                )
                if fg is not None and (
                    fg.rgb not in (None, "00000000")
                    or fg.theme not in (None, 0)
                    or fg.indexed not in (None, 64)
                ):
                    hits.append(
                        f"{cell.coordinate}={getattr(fg, 'rgb', None) or f'theme{fg.theme}' or fg.indexed}"
                    )
        if hits:
            out.append(
                f"### Sheet: {ws.title} highlighted cells: {', '.join(hits[:200])}"
            )
    return "\n".join(out)


def serialize_task_workbook(task: dict) -> str:
    text = serialize_workbook(task["init_xlsx"])
    if _FILL_TRIGGER.search(task.get("instruction", "")):
        extra = _fill_lines(task["init_xlsx"])
        if extra:
            text += "\n\n" + extra
    if len(text) > MAX_WORKBOOK_CHARS:
        text = (
            text[:MAX_WORKBOOK_CHARS]
            + "\n\n[TRUNCATED — workbook larger than 20k chars; "
        )
        "big data regions summarized above; answer range cells included where visible]"
    return text
