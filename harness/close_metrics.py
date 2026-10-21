"""Close metrics — what the product actually did, measured.

The pilot plan in `docs/COREWEAVE.md` names the measures that decide whether
this is worth paying for: reviewer minutes, correct recurring resolutions,
incorrect suggestions, unresolved or reopened exceptions, and audit-record
completeness. This module computes them from the two stores that already hold
the truth — the exception queue and the decision ledger — so the answer is a
query rather than an opinion.

Two decisions about what these numbers are, because the difference matters when
they go in front of a customer:

**Reviewer minutes is time-to-decision, not time spent.** The clock starts when
the exception is raised and stops when it is decided. A reviewer who leaves the
queue open overnight inflates it. The honest name is "minutes in queue"; the
plan calls it reviewer minutes because it is the closest thing the system can
observe without watching the reviewer, and the report says so in words rather
than implying precision it does not have.

**A reopened exception is a join, not a counter.** The cell reference moves
between periods — the same transaction sits at a different row next quarter — so
the join is on the scope tuple plus the narrative alias, which is the same
identity the governed-memory rules use (`memory_policy.alias_key`). That is
deliberately the same notion of "the same thing" throughout the system.

Everything here reports on a named dataset and a named period. A number without
both is not a result.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

from memory_policy import alias_key
from tenant import tenant_of_scope


@dataclass
class CloseMetrics:
    """What one close produced, and what it cost."""

    tenant: str = ""
    period: str = ""
    dataset: str = ""
    exceptions_raised: int = 0
    decisions_recorded: int = 0
    approved: int = 0
    rejected: int = 0
    still_pending: int = 0
    minutes_to_decide_median: float | None = None
    minutes_to_decide_slowest: float | None = None
    rules_active: int = 0
    suggestions_offered: int = 0
    suggestions_accepted: int = 0
    reopened: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "tenant": self.tenant,
            "period": self.period,
            "dataset": self.dataset,
            "exceptions_raised": self.exceptions_raised,
            "decisions_recorded": self.decisions_recorded,
            "approved": self.approved,
            "rejected": self.rejected,
            "still_pending": self.still_pending,
            "minutes_to_decide_median": self.minutes_to_decide_median,
            "minutes_to_decide_slowest": self.minutes_to_decide_slowest,
            "rules_active": self.rules_active,
            "suggestions_offered": self.suggestions_offered,
            "suggestions_accepted": self.suggestions_accepted,
            "reopened": self.reopened,
            "notes": self.notes,
        }

    def render(self) -> str:
        """A readable report. Every number names what it counts."""
        lines = [
            f"Close metrics — tenant {self.tenant or 'unbound'}",
            f"  period:   {self.period or 'unspecified'}",
            f"  dataset:  {self.dataset or 'unspecified'}",
            "",
            f"  exceptions raised      {self.exceptions_raised}",
            f"  decisions recorded     {self.decisions_recorded}"
            f"   (approved {self.approved}, rejected {self.rejected})",
            f"  still pending          {self.still_pending}",
        ]
        if self.minutes_to_decide_median is not None:
            lines.append(
                f"  minutes in queue       median {self.minutes_to_decide_median:.1f}"
                f", slowest {self.minutes_to_decide_slowest:.1f}"
            )
        lines.extend(
            [
                f"  governed rules active  {self.rules_active}",
                f"  suggestions offered    {self.suggestions_offered}",
                f"  suggestions accepted   {self.suggestions_accepted}",
                f"  reopened exceptions    {len(self.reopened)}",
            ]
        )
        for note in self.notes:
            lines.append(f"  note: {note}")
        return "\n".join(lines)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _minutes_between(start: str | None, end: str | None) -> float | None:
    began = _parse_time(start)
    finished = _parse_time(end)
    if began is None or finished is None:
        return None
    delta = (finished - began).total_seconds() / 60.0
    return max(delta, 0.0)


def exception_identity(exception: dict) -> tuple[str, str]:
    """The identity of an exception across periods: scope plus alias.

    The cell reference is deliberately not part of it — a cell's row moves
    between closes, but the entity, account and narrative do not.
    """
    scope = exception.get("scope") or {}
    try:
        tenant = tenant_of_scope(scope)
    except (TypeError, ValueError):
        tenant = str(scope.get("tenant", ""))
    entity = str(scope.get("entity", ""))
    account = str(scope.get("account", ""))
    narrative = str(exception.get("narrative", ""))
    alias = alias_key(narrative) if narrative else ""
    return (f"{tenant}|{entity}|{account}", alias)


def measure_close(
    payloads: list[dict],
    ledger=None,
    store=None,
    period: str = "",
    dataset: str = "",
    tenant: str = "",
) -> CloseMetrics:
    """Measure one close from its exception queue and, optionally, its ledger.

    `payloads` is what `exceptions.load_exceptions` returns. `ledger` is a
    `ledger.DecisionLedger`; `store` is a `memory_store.MemoryStore`. Both are
    optional so the module works against artifacts alone.
    """
    metrics = CloseMetrics(tenant=tenant, period=period, dataset=dataset)
    if not tenant and store is not None:
        metrics.tenant = store.tenant or ""

    raised = 0
    for payload in payloads:
        for exception in payload.get("exceptions", []) or []:
            raised += 1
            if exception.get("status") == "pending":
                metrics.still_pending += 1
    metrics.exceptions_raised = raised

    durations: list[float] = []
    if ledger is not None:
        recorded = ledger.decisions()
        metrics.decisions_recorded = len(recorded)
        for entry in recorded:
            if entry.get("decision") == "approved":
                metrics.approved += 1
            elif entry.get("decision") == "rejected":
                metrics.rejected += 1
            minutes = _minutes_between(entry.get("raised_at"), entry.get("created_at"))
            if minutes is not None:
                durations.append(minutes)
        if durations:
            metrics.minutes_to_decide_median = round(statistics.median(durations), 2)
            metrics.minutes_to_decide_slowest = round(max(durations), 2)
            metrics.notes.append(
                "minutes in queue is time from the exception being raised to the "
                "decision being recorded — it includes time the reviewer was not "
                "looking at, so it is an upper bound on review effort, not a "
                "measure of it."
            )

    if store is not None:
        metrics.rules_active = sum(
            1 for rule in store.rules() if rule.get("status") == "active"
        )

    return metrics


def reopened_exceptions(
    current_payloads: list[dict],
    ledger=None,
    previous_aliases: set[tuple[str, str]] | None = None,
) -> list[dict]:
    """Exceptions in this close whose identity was already decided before.

    `previous_aliases` is the set of (scope, alias) pairs decided in earlier
    periods. A pair appearing again means the same question came back — either
    the rule did not cover it, or the rule was wrong about it, and both are
    worth seeing.
    """
    if not previous_aliases:
        return []
    reopened: list[dict] = []
    for payload in current_payloads:
        for exception in payload.get("exceptions", []) or []:
            identity = exception_identity(exception)
            if identity in previous_aliases:
                reopened.append(
                    {
                        "cell": exception.get("cell", ""),
                        "task": payload.get("task_id", ""),
                        "reason": exception.get("reason", ""),
                        "identity": "|".join(identity),
                    }
                )
    return reopened


def decided_aliases(payloads: list[dict], tenant: str = "") -> set[tuple[str, str]]:
    """The identities decided in a close — the input to the next close's reopen check."""
    found: set[tuple[str, str]] = set()
    for payload in payloads:
        for exception in payload.get("exceptions", []) or []:
            if exception.get("status") in ("approved", "rejected"):
                found.add(exception_identity(exception))
    return found


def main() -> int:
    """Report the metrics for one close.

    Usage:
        python harness/close_metrics.py <exceptions.json> [--ledger FILE]
                                      [--memory FILE] [--period LABEL]
                                      [--dataset LABEL] [--tenant LABEL]
    """
    import argparse
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
    from exceptions import load_exceptions

    parser = argparse.ArgumentParser(description="Close metrics")
    parser.add_argument("path", help="path to exceptions.json")
    parser.add_argument("--ledger", default=None, help="decision ledger file")
    parser.add_argument("--memory", default=None, help="governed memory store")
    parser.add_argument("--period", default="", help="the period this close covers")
    parser.add_argument("--dataset", default="", help="where the data came from")
    parser.add_argument("--tenant", default="", help="the tenant this close belongs to")
    args = parser.parse_args()

    payloads, _ = load_exceptions(Path(args.path))
    ledger = None
    store = None
    try:
        if args.ledger:
            from ledger import DecisionLedger

            ledger = DecisionLedger(Path(args.ledger))
        if args.memory:
            from memory_store import MemoryStore

            store = MemoryStore(Path(args.memory))
        metrics = measure_close(
            payloads,
            ledger=ledger,
            store=store,
            period=args.period,
            dataset=args.dataset,
            tenant=args.tenant,
        )
    finally:
        if ledger is not None:
            ledger.close()
        if store is not None:
            store.close()
    print(metrics.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
