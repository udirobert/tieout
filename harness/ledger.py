"""The decision ledger — an append-only record of what a human decided, and why.

The exception queue today is a mutable file: `apply_decisions` rewrites
`exceptions.json` on every review, so the current state is all that survives.
That is fine for a queue and useless as an audit trail, and an audit trail is
what a fund admin's reviewer, a regulator, or a customer's own auditor will
ask for. "Who decided this cell, when, on what evidence, and what did it
change from?"

So decisions get their own store. It is append-only — nothing is ever updated
or deleted in normal operation — and it lives beside the workbook rather than
inside it, so deleting a run directory does not erase what was decided.

Three properties this module is built around:

* **It outlives the artefact.** The ledger records what happened; the workbook
  records the result. Deleting the second does not touch the first.
* **It is ordered.** An autoincrement sequence gives a strict order across
  tasks, so "what did the reviewer do next" has an answer.
* **It is exportable.** `export()` produces the whole tenant's record in one
  JSON document, which is the form a retention or export policy needs.

The ledger is deliberately *not* the exception queue. The queue is a work list
that is rewritten; the ledger is a history that is not.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from evidence import Decision
from tenant_store import TenantStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    tenant TEXT NOT NULL DEFAULT '',
    task_id TEXT NOT NULL DEFAULT '',
    cell TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL DEFAULT '',
    tenant_scope TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS decisions_tenant_idx ON decisions(tenant, seq);
CREATE INDEX IF NOT EXISTS decisions_cell_idx ON decisions(tenant, task_id, cell);
"""

DECISION_RECORDED = "decision_recorded"
DECISION_APPLIED = "decision_applied"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionLedger(TenantStore):
    """Append-only record of review decisions, bound to one tenant."""

    SCHEMA = SCHEMA
    TENANT_TABLES = ("decisions",)

    def record(
        self,
        decision: Decision,
        reviewer: str = "",
        created_at: str | None = None,
    ) -> dict:
        """Append one decision. Never updates an existing row."""
        tenant = self._bind_scope(decision)
        record = decision.as_record()
        record.update(
            {
                "decision": decision.status,
                "reviewer": reviewer,
                "created_at": created_at or _now(),
            }
        )
        row_id = f"dec-{self._next_seq():012d}"
        self._conn.execute(
            "INSERT INTO decisions (id, tenant, task_id, cell, decision, reviewer, "
            "tenant_scope, created_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row_id,
                tenant,
                decision.task_id,
                decision.cell,
                decision.status,
                reviewer,
                decision.tenant,
                record["created_at"],
                json.dumps(record, ensure_ascii=False, allow_nan=False),
            ),
        )
        return {"decision_id": row_id, **record}

    def _bind_scope(self, decision: Decision) -> str:
        """Bind the ledger to the decision's scope tenant, or check it."""
        scope = {"tenant": decision.tenant} if decision.tenant else None
        if scope is None:
            if self.tenant is None:
                return ""
            return self.tenant
        return self._bind_tenant(scope)

    def _next_seq(self) -> int:
        row = self._conn.execute("SELECT MAX(seq) FROM decisions").fetchone()
        return (row[0] or 0) + 1

    def decisions(
        self, task_id: str | None = None, cell: str | None = None
    ) -> list[dict]:
        """Every recorded decision, oldest first."""
        clauses = []
        params: list[str] = []
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if cell is not None:
            clauses.append("cell = ?")
            params.append(cell)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn.execute(
            "SELECT id, tenant, task_id, cell, decision, reviewer, created_at, payload "
            f"FROM decisions{where} ORDER BY seq",
            params,
        ).fetchall()
        return [
            {
                "decision_id": row[0],
                "tenant": row[1],
                "task_id": row[2],
                "cell": row[3],
                "decision": row[4],
                "reviewer": row[5],
                "created_at": row[6],
                **json.loads(row[7]),
            }
            for row in rows
            if self._visible(row[1])
        ]

    def export(self) -> dict:
        """Everything this tenant has on file, as one JSON document."""
        return {
            "tenant": self.tenant,
            "exported_at": _now(),
            "decisions": self.decisions(),
        }

    def _backfill_tenants(self) -> None:
        """Backfill the tenant column from the scope inside each payload."""
        for row_id, payload_text in self._row_tenants("decisions"):
            try:
                payload = json.loads(payload_text)
            except (TypeError, ValueError):
                continue
            tenant = payload.get("tenant") if isinstance(payload, dict) else None
            if tenant:
                self._set_row_tenant("decisions", row_id, str(tenant))
