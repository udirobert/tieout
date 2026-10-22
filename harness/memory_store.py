from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from memory_policy import (
    candidate_from_correction,
    checked_record,
    replay,
    required_text,
    resolve,
)
from hmem_client import HmemUnavailable
from tenant import CrossTenantWrite
from tenant_store import TenantStore

SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (id TEXT PRIMARY KEY, tenant TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rules (id TEXT PRIMARY KEY, tenant TEXT NOT NULL DEFAULT '', correction_id TEXT NOT NULL REFERENCES corrections(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, tenant TEXT NOT NULL DEFAULT '', rule_id TEXT, kind TEXT NOT NULL, reviewer TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hmem_links (kind TEXT NOT NULL, local_id TEXT NOT NULL, hmem_id TEXT NOT NULL, PRIMARY KEY (kind, local_id));
"""

CORRECTION_APPROVED = "correction_approved"
RULE_PROPOSED = "rule_proposed"
RULE_VALIDATED = "rule_validated"
RULE_ACTIVATED = "rule_activated"
RULE_REVOKED = "rule_revoked"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _freeze(value):
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


class MemoryStore(TenantStore):
    """The governed business-memory store: corrections, rules, and their events.

    One file belongs to one tenant. A record whose scope names another tenant
    is refused on write, and rows belonging to another tenant are never
    returned by a read — the isolation is structural, not a convention callers
    are trusted to honour.

    An optional H-MEM engine client (`hmem`) adds the parts SQLite does not:
    hybrid-scored recall, layered promotion, and the engine's own append-only
    trust ledger. The division of authority stays where it was — the SQLite
    tables are the system of record for the governed lifecycle and the replay
    gate; the engine stores the recallable content and independently logs what
    the substrate did. `suggest` keeps `resolve` as the decision and attaches
    engine recall as advisory evidence only. When the engine is unreachable
    every operation degrades to the pre-engine behaviour: corrections still
    record, rules still govern, suggestions still resolve — `recall` is simply
    absent. A client naming a different tenant than the bound store is a
    `CrossTenantWrite`, not a fallback.
    """

    SCHEMA = SCHEMA
    TENANT_TABLES = ("corrections", "rules", "events")

    def __init__(self, path: Path, tenant: str | None = None, hmem=None):
        super().__init__(path, tenant)
        self._hmem = hmem

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def _tx(self, immediate: bool = False):
        self._conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        self._conn.execute("COMMIT")

    def _event(
        self, kind: str, rule_id, reviewer: str, data: dict, tenant: str = ""
    ) -> dict:
        event = {
            "event_id": str(uuid.uuid4()),
            "kind": kind,
            "rule_id": rule_id,
            "reviewer": reviewer,
            "created_at": _now(),
            "data": _freeze(data),
        }
        self._conn.execute(
            "INSERT INTO events (id, tenant, rule_id, kind, reviewer, created_at, payload) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event["event_id"],
                tenant,
                rule_id,
                kind,
                reviewer,
                event["created_at"],
                json.dumps(event["data"], ensure_ascii=False, allow_nan=False),
            ),
        )
        return event

    def _rule_events(self, rule_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, kind, reviewer, created_at, payload FROM events WHERE rule_id = ? ORDER BY seq",
            (rule_id,),
        ).fetchall()
        return [
            {
                "event_id": row[0],
                "kind": row[1],
                "rule_id": rule_id,
                "reviewer": row[2],
                "created_at": row[3],
                "data": json.loads(row[4]),
            }
            for row in rows
        ]

    def _rule_row(self, rule_id: str):
        return self._conn.execute(
            "SELECT id, tenant, payload FROM rules WHERE id = ?", (rule_id,)
        ).fetchone()

    def _state(self, rule_id: str) -> dict:
        row = self._rule_row(rule_id)
        if row is None:
            raise KeyError(f"unknown rule: {rule_id}")
        status = "candidate"
        validation = None
        activation = None
        for event in self._rule_events(rule_id):
            if event["kind"] == RULE_VALIDATED:
                status, validation = "validated", event
            elif event["kind"] == RULE_ACTIVATED:
                status, activation = "active", event
            elif event["kind"] == RULE_REVOKED:
                status = "revoked"
        return {
            "rule": json.loads(row[2]),
            "status": status,
            "validation": validation,
            "activation": activation,
        }

    def _active_rules(self) -> list[dict]:
        rows = self._conn.execute("SELECT id, tenant FROM rules ORDER BY id").fetchall()
        return [
            state["rule"]
            for (row_id, row_tenant) in rows
            if self._visible(row_tenant)
            for state in [self._state(row_id)]
            if state["status"] == "active"
        ]

    def record_correction(
        self, record: dict, vendor: str, reviewer: str, rationale: str
    ) -> dict:
        record = checked_record(record)
        tenant = self._bind_tenant(record["scope"])
        correction = {
            "correction_id": str(uuid.uuid4()),
            "record": record,
            "vendor": required_text(vendor, "vendor"),
            "reviewer": required_text(reviewer, "reviewer"),
            "rationale": required_text(rationale, "rationale"),
            "created_at": _now(),
        }
        with self._tx():
            self._conn.execute(
                "INSERT INTO corrections (id, tenant, payload) VALUES (?, ?, ?)",
                (
                    correction["correction_id"],
                    tenant,
                    json.dumps(correction, ensure_ascii=False, allow_nan=False),
                ),
            )
            self._event(
                CORRECTION_APPROVED, None, correction["reviewer"], correction, tenant
            )
            hmem_id = self._engine_add(
                content=(
                    f"{record['narrative']} — vendor {correction['vendor']}: "
                    f"{correction['rationale']}"
                ),
                source="user_correction",
                layer="working",
                tags=["correction", correction["vendor"]],
            )
            if hmem_id:
                self._link("correction", correction["correction_id"], hmem_id)
        return _freeze(correction)

    def propose(self, correction_id: str) -> dict:
        correction_id = required_text(correction_id, "correction_id")
        with self._tx():
            row = self._conn.execute(
                "SELECT tenant, payload FROM corrections WHERE id = ?", (correction_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown correction: {correction_id}")
            tenant = row[0]
            rule = candidate_from_correction(json.loads(row[1]), str(uuid.uuid4()))
            self._conn.execute(
                "INSERT INTO rules (id, tenant, correction_id, payload) VALUES (?, ?, ?, ?)",
                (
                    rule["rule_id"],
                    tenant,
                    correction_id,
                    json.dumps(rule, ensure_ascii=False, allow_nan=False),
                ),
            )
            self._event(RULE_PROPOSED, rule["rule_id"], rule["reviewer"], rule, tenant)
            corr_mem = self._engine_id("correction", correction_id)
            hmem_id = self._engine_add(
                content=(
                    f"{rule['alias']} → vendor {rule['vendor']}: {rule['rationale']}"
                ),
                source="rule_proposal",
                layer="working",
                tags=["rule", rule["vendor"]],
                derived_from=[corr_mem] if corr_mem else None,
            )
            if hmem_id:
                self._link("rule", rule["rule_id"], hmem_id)
        return _freeze(rule)

    def validate(self, rule_id: str, cases: list[dict], reviewer: str) -> dict:
        rule_id = required_text(rule_id, "rule_id")
        reviewer = required_text(reviewer, "reviewer")
        cases = _freeze(cases)
        with self._tx():
            state = self._state(rule_id)
            if state["status"] == "revoked":
                raise ValueError(f"rule is revoked: {rule_id}")
            if state["status"] == "active":
                raise ValueError(f"rule is already active: {rule_id}")
            report = replay(state["rule"], cases, self._active_rules())
            self._event(
                RULE_VALIDATED,
                rule_id,
                reviewer,
                {"cases": cases, "report": report, "candidate": state["rule"]},
                self._rule_tenant(rule_id),
            )
        return _freeze(report)

    def activate(self, rule_id: str, reviewer: str) -> dict:
        rule_id = required_text(rule_id, "rule_id")
        reviewer = required_text(reviewer, "reviewer")
        with self._tx(immediate=True):
            state = self._state(rule_id)
            if state["status"] == "revoked":
                raise ValueError(f"rule is revoked: {rule_id}")
            if state["status"] == "active":
                raise ValueError(f"rule is already active: {rule_id}")
            if state["validation"] is None:
                raise ValueError(f"rule has no validation: {rule_id}")
            stored = state["validation"]["data"]
            fresh = replay(stored["candidate"], stored["cases"], self._active_rules())
            if fresh["active_rules_digest"] != stored["report"]["active_rules_digest"]:
                raise ValueError(
                    f"active rules changed since validation; revalidate rule: {rule_id}"
                )
            if not stored["report"]["eligible"] or not fresh["eligible"]:
                raise ValueError(f"rule is not eligible for activation: {rule_id}")
            event = self._event(
                RULE_ACTIVATED,
                rule_id,
                reviewer,
                {"candidate": stored["candidate"], "report": fresh},
                self._rule_tenant(rule_id),
            )
            mid = self._engine_id("rule", rule_id)
            if mid:
                self._engine_op(lambda e: e.promote(mid, "long_term"))
        return _freeze(event)

    def revoke(self, rule_id: str, reviewer: str, reason: str) -> dict:
        rule_id = required_text(rule_id, "rule_id")
        reviewer = required_text(reviewer, "reviewer")
        reason = required_text(reason, "reason")
        with self._tx():
            state = self._state(rule_id)
            if state["status"] != "active":
                raise ValueError(f"rule is not active: {rule_id}")
            event = self._event(
                RULE_REVOKED,
                rule_id,
                reviewer,
                {"reason": reason},
                self._rule_tenant(rule_id),
            )
            mid = self._engine_id("rule", rule_id)
            if mid:
                self._engine_op(lambda e: e.supersede(mid, "revoked"))
        return _freeze(event)

    def _rule_tenant(self, rule_id: str) -> str:
        row = self._rule_row(rule_id)
        return row[1] if row else ""

    # -- H-MEM engine seam -------------------------------------------------
    #
    # SQLite stays the system of record; the engine calls below are additive
    # and only ever skipped, never faked. They run inside the SQLite
    # transaction deliberately: a commit that succeeds leaves a consistent
    # link row, and a rollback leaves an unlinked engine record, which is
    # benign recall data, not truth.

    def _engine(self):
        """The bound tenant's engine client, or None when recall is off.

        An unbound store cannot use the engine (no tenant to trust), and a
        client that names a different tenant than the bound store is refused
        outright rather than quietly ignored.
        """
        if self._hmem is None or self._tenant is None:
            return None
        if self._hmem.tenant != self._tenant:
            raise CrossTenantWrite(
                f"engine client for tenant {self._hmem.tenant!r} cannot write "
                f"to the store for {self._tenant!r}"
            )
        return self._hmem

    def _engine_add(
        self,
        *,
        content: str,
        source: str,
        layer: str,
        tags: list,
        derived_from: list | None = None,
    ) -> str | None:
        engine = self._engine()
        if engine is None:
            return None
        try:
            rec = engine.add(
                content=content,
                source=source,
                layer=layer,
                tags=tags,
                derivedFrom=derived_from or [],
            )
        except HmemUnavailable:
            return None
        return rec.get("id") if isinstance(rec, dict) else None

    def _link(self, kind: str, local_id: str, hmem_id: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO hmem_links (kind, local_id, hmem_id) VALUES (?, ?, ?)",
            (kind, local_id, hmem_id),
        )

    def _engine_id(self, kind: str, local_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT hmem_id FROM hmem_links WHERE kind = ? AND local_id = ?",
            (kind, local_id),
        ).fetchone()
        return row[0] if row else None

    def _engine_op(self, fn) -> None:
        engine = self._engine()
        if engine is None:
            return
        try:
            fn(engine)
        except HmemUnavailable:
            return

    def _recall(self, record: dict) -> list[dict] | None:
        engine = self._engine()
        if engine is None:
            return None
        text = f"{record['narrative']} {record['vendor_hint']}".strip()
        try:
            result = engine.query(text, topN=5)
        except HmemUnavailable:
            return None
        return [
            {
                "memory_id": item["memory"]["id"],
                "content": item["memory"]["content"],
                "layer": item["memory"]["layer"],
                "score": item["relevance"],
                "superseded": bool(item["memory"].get("supersededBy")),
            }
            for item in result.get("memories", [])
        ]

    def _backfill_tenants(self) -> None:
        """Backfill rows, then give each event the tenant of its rule."""
        super()._backfill_tenants()
        rule_tenants = {
            row[0]: row[1]
            for row in self._conn.execute("SELECT id, tenant FROM rules").fetchall()
        }
        for row_id, payload_text in self._row_tenants("events"):
            try:
                payload = json.loads(payload_text)
            except (TypeError, ValueError):
                continue
            rule_id = payload.get("rule_id") if isinstance(payload, dict) else None
            if rule_id and rule_id in rule_tenants and rule_tenants[rule_id]:
                self._set_row_tenant("events", row_id, rule_tenants[rule_id])

    def corrections(self) -> list[dict]:
        """Every correction this tenant has recorded, oldest first."""
        rows = self._conn.execute(
            "SELECT id, tenant, payload FROM corrections ORDER BY id"
        ).fetchall()
        return [
            {"correction_id": row[0], **json.loads(row[2])}
            for row in rows
            if self._visible(row[1])
        ]

    def export(self) -> dict:
        """Everything this tenant has on file, as one JSON-serialisable document.

        The export is the retention/deletion policy made concrete: it is the
        complete record of what was decided and why, and it outlives the
        workbook it describes.
        """
        return {
            "tenant": self.tenant,
            "exported_at": _now(),
            "corrections": self.corrections(),
            "rules": self.rules(),
            "history": self.history(),
        }

    def rules(self) -> list[dict]:
        rows = self._conn.execute("SELECT id, tenant FROM rules ORDER BY id").fetchall()
        return [
            {
                "rule": state["rule"],
                "status": state["status"],
                "validation": state["validation"]["data"]["report"]
                if state["validation"]
                else None,
                "activation": state["activation"],
            }
            for (row_id, row_tenant) in rows
            if self._visible(row_tenant)
            for state in [self._state(row_id)]
        ]

    def history(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, rule_id, kind, reviewer, created_at, payload, tenant FROM events ORDER BY seq"
        ).fetchall()
        return [
            {
                "event_id": row[0],
                "kind": row[2],
                "rule_id": row[1],
                "reviewer": row[3],
                "created_at": row[4],
                "data": json.loads(row[5]),
                "tenant": row[6],
            }
            for row in rows
            if self._visible(row[6])
        ]

    def suggest(self, records: list[dict]) -> list[dict]:
        active = self._active_rules()
        out = []
        for item in records:
            record = checked_record(item)
            suggestion = {"record": record, **resolve(record, active)}
            recall = self._recall(record)
            if recall is not None:
                suggestion["recall"] = recall
            out.append(suggestion)
        return out
