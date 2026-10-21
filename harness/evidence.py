"""The evidence model — one representation of "why was this cell flagged".

This module exists because the evidence was being rendered three separate ways
and drifting. The CLI printed `Staging Sheet row 6 (key=NIP PLATFORM...)`; the
console showed a reason string with nothing behind it; the walkthrough showed
something else again. Three surfaces, three formats, and the headline claim —
"the source rows that say why" — true in one of them.

So the shape lives here, once, and every surface renders *this*:

* `EvidenceRow` — one source row: where it is, and what a human should read.
* `Decision` — the unit of review: the cell, the value it holds now, the value
  proposed for it, why, and the evidence behind that why.

The important property is that `Decision` is *complete before a decision is
made*. The current value is read from the init workbook, the proposed value
from the output workbook, and the evidence from the source rows — so a
reviewer sees the diff, not just a proposal. The write path (`apply_decisions`)
already had this information; it just never showed it.

Three renderings, one model:

* the CLI prints `Decision.render_line()`,
* the console and the customer surface build a table from `Decision.as_row()`,
* the ledger stores `Decision.as_record()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceRow:
    """One source row that supports (or contradicts) a flagged cell."""

    sheet: str
    row: int
    key: str

    @property
    def label(self) -> str:
        """How a human reads this row. Defined once, here."""
        return f"{self.sheet} r{self.row} · {self.key}"

    def as_dict(self) -> dict:
        return {"sheet": self.sheet, "row": self.row, "key": self.key}

    @classmethod
    def from_dict(cls, value: dict) -> "EvidenceRow":
        return cls(
            sheet=str(value.get("sheet", "")),
            row=int(value.get("row", 0)),
            key=str(value.get("key", "")),
        )


@dataclass(frozen=True)
class Decision:
    """A flagged cell, its evidence, and the change under review."""

    cell: str
    current_value: str
    proposed_value: str
    reason: str
    evidence: tuple[EvidenceRow, ...] = ()
    status: str = "pending"
    task_id: str = ""
    tenant: str = ""
    raised_at: str = ""

    def __post_init__(self) -> None:
        """Normalise the values, so every way of building a Decision agrees.

        A blank cell is shown as "(blank)" and never as an empty string: an
        empty string and a blank cell look identical in a table, and the whole
        point of the diff is to tell them apart.
        """
        object.__setattr__(self, "current_value", _stringify(self.current_value))
        object.__setattr__(self, "proposed_value", _stringify(self.proposed_value))
        object.__setattr__(self, "evidence", tuple(self.evidence or ()))

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        return self.status == "rejected"

    @property
    def diff_label(self) -> str:
        """The before → after pair, in one line."""
        return f"{_render(self.current_value)} → {_render(self.proposed_value)}"

    @property
    def evidence_label(self) -> str:
        """Every evidence row on one line, or a note when there is none."""
        if not self.evidence:
            return "no source rows found"
        return "; ".join(row.label for row in self.evidence)

    def render_line(self) -> str:
        """The CLI's rendering of one decision."""
        return (
            f"  {self.cell} | {self.reason} | {self.diff_label}\n"
            f"    evidence: {self.evidence_label}"
        )

    def as_row(self) -> dict:
        """A flat row for a table."""
        return {
            "cell": self.cell,
            "reason": self.reason,
            "current": _render(self.current_value),
            "proposed": _render(self.proposed_value),
            "evidence": self.evidence_label,
            "status": self.status,
        }

    def as_record(self) -> dict:
        """The durable form written to the decision ledger."""
        return {
            "cell": self.cell,
            "task_id": self.task_id,
            "tenant": self.tenant,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "reason": self.reason,
            "status": self.status,
            "raised_at": self.raised_at,
            "evidence": [row.as_dict() for row in self.evidence],
        }

    @classmethod
    def from_exception(
        cls,
        exception: dict,
        current_value: Any = "",
        task_id: str = "",
        tenant: str = "",
    ) -> "Decision":
        """Build a decision from an `exceptions.json` entry plus the init value."""
        rows = tuple(
            EvidenceRow.from_dict(row)
            for row in exception.get("evidence_rows", []) or []
        )
        return cls(
            cell=str(exception.get("cell", "")),
            current_value=_stringify(current_value),
            proposed_value=_stringify(exception.get("proposed_value", "")),
            reason=str(exception.get("reason", "")),
            evidence=rows,
            status=str(exception.get("status", "pending")),
            task_id=task_id,
            tenant=tenant,
            raised_at=str(exception.get("raised_at", "") or ""),
        )


def _stringify(value: Any) -> str:
    """Render a cell value for a human: blank is explicit, never an empty string."""
    if value is None or value == "":
        return "(blank)"
    return str(value)


def _render(value: Any) -> str:
    """Render a cell value compactly for a diff."""
    if value is None or value == "":
        return "(blank)"
    text = str(value)
    return text if len(text) <= 60 else text[:57] + "…"
