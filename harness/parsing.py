"""tieout parsing — lenient answer + codegen parsers.

Handles: <think> blocks, code fences, prose around JSON, concatenated JSON objects,
bare {"cell","value"} dicts without the "cells" wrapper, sheet-qualified refs (Sheet1!B6).
"""

import json
import re

from pydantic import BaseModel, Field


class CellValue(BaseModel):
    cell: str
    value: str | int | float | bool | None = None
    sheet: str | None = None


class Answer(BaseModel):
    cells: list[CellValue] = Field(default_factory=list)


def cell_ref(sheet: str | None, coord: str) -> str:
    """Stable graded-cell key: 'Sheet1!B6' when a sheet is known, else 'B6'."""
    sheet = (sheet or "").strip()
    return f"{sheet}!{coord}" if sheet else coord


def _first_json(text: str):
    """First JSON object or array via raw_decode; fall back to span on decode error."""
    start_brace = text.find("{")
    start_bracket = text.find("[")
    starts = [i for i in (start_brace, start_bracket) if i >= 0]
    if not starts:
        raise ValueError(f"no JSON object or array in reply: {text[:120]!r}")
    start = min(starts)
    try:
        return json.JSONDecoder().raw_decode(text[start:])[0]
    except json.JSONDecodeError:
        end_char = "}" if text[start] == "{" else "]"
        end = text.rfind(end_char)
        if end >= start:
            return json.loads(text[start : end + 1])
        raise


def _plain_number(token: str) -> bool:
    if token in ("", ".", "+", "-", "+.", "-."):
        return False
    try:
        float(token)
    except ValueError:
        return False
    return True


def normalize_cell_value(value):
    """Numeric strings → int/float. Do not strip text: goldens keep padding.

    Scorer requires type(gold)==type(pred) after its 2dp round, so '42' ≠ 42.
    'AAMRANET ' / ' Sales' stay padded (61-4, 80-42, 341-40). '001' stays text.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if not isinstance(value, str):
        return value
    token = value.strip()
    if not _plain_number(token):
        return value
    if token.startswith("0") and token not in ("0",) and not token.startswith("0."):
        return value
    n = float(token)
    if n.is_integer() and "." not in token and "e" not in token.lower():
        return int(n)
    return n


def _normalize_cell(c: CellValue) -> None:
    raw = (c.cell or "").strip()
    if "!" in raw:
        sheet_part, coord = raw.rsplit("!", 1)
        if not c.sheet:
            c.sheet = sheet_part.replace("'", "").replace('"', "").strip() or None
        raw = coord
    c.cell = raw.replace("$", "").strip().upper()
    if c.sheet:
        c.sheet = c.sheet.replace("'", "").replace('"', "").strip() or None
    c.value = normalize_cell_value(c.value)


def parse_answer(text: str) -> Answer:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"```(?:json)?", "", text)
    obj = _first_json(text)
    if isinstance(obj, list):  # bare list of cell dicts
        obj = {"cells": obj}
    elif isinstance(obj, dict) and "cells" not in obj and "cell" in obj:
        obj = {"cells": [obj]}
    ans = Answer.model_validate(obj)
    for c in ans.cells:
        _normalize_cell(c)
    return ans


def parse_code(text: str) -> str:
    """Extract a Python script from a model reply (fenced or bare)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    if m:
        return m.group(1).strip()
    text = re.sub(r"^```(?:python)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    return text.strip()
