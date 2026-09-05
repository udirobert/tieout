"""tieout parsing — lenient answer parser (the biggest free win, per docs/PATTERNS.md).

Handles: <think> blocks, code fences, prose around JSON, concatenated JSON objects,
bare {"cell","value"} dicts without the "cells" wrapper, sheet-qualified refs (Sheet1!B6).
"""

import json
import re

from pydantic import BaseModel, Field


class CellValue(BaseModel):
    cell: str
    value: str | int | float | bool | None = None


class Answer(BaseModel):
    cells: list[CellValue] = Field(default_factory=list)


def _first_json(text: str):
    """First JSON object via raw_decode; fall back to braces span on decode error."""
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON object in reply: {text[:120]!r}")
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except json.JSONDecodeError:
        return json.loads(text[start : text.rfind("}") + 1])


def parse_answer(text: str) -> Answer:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    obj = _first_json(text)
    if isinstance(obj, list):  # bare list of cell dicts
        obj = {"cells": obj}
    elif isinstance(obj, dict) and "cells" not in obj and "cell" in obj:
        obj = {"cells": [obj]}
    ans = Answer.model_validate(obj)
    for c in ans.cells:  # Sheet1!B6 -> B6; $B$6 -> B6
        c.cell = c.cell.split("!")[-1].replace("$", "").strip().upper()
    return ans
