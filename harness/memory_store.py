from __future__ import annotations

import json
import os
import sqlite3
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

SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rules (id TEXT PRIMARY KEY, correction_id TEXT NOT NULL REFERENCES corrections(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE, rule_id TEXT, kind TEXT NOT NULL, reviewer TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
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


class MemoryStore:
    def __init__(self, path: Path):
        path = Path(path)
        if not path.parent.is_dir():
            raise FileNotFoundError(f"memory database directory does not exist: {path.parent}")
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600))
        except FileExistsError:
            pass
        self._conn = sqlite3.connect(str(path), isolation_level=None)
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.executescript(SCHEMA)
        except BaseException:
            self._conn.close()
            raise

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

    def _event(self, kind: str, rule_id, reviewer: str, data: dict) -> dict:
        event = {
            "event_id": str(uuid.uuid4()),
            "kind": kind,
            "rule_id": rule_id,
            "reviewer": reviewer,
            "created_at": _now(),
            "data": _freeze(data),
        }
        self._conn.execute(
            "INSERT INTO events (id, rule_id, kind, reviewer, created_at, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (event["event_id"], rule_id, kind, reviewer, event["created_at"], json.dumps(event["data"], ensure_ascii=False, allow_nan=False)),
        )
        return event

    def _rule_events(self, rule_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, kind, reviewer, created_at, payload FROM events WHERE rule_id = ? ORDER BY seq",
            (rule_id,),
        ).fetchall()
        return [
            {"event_id": row[0], "kind": row[1], "rule_id": rule_id, "reviewer": row[2], "created_at": row[3], "data": json.loads(row[4])}
            for row in rows
        ]

    def _rule_row(self, rule_id: str):
        return self._conn.execute("SELECT id, payload FROM rules WHERE id = ?", (rule_id,)).fetchone()

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
        return {"rule": json.loads(row[1]), "status": status, "validation": validation, "activation": activation}

    def _active_rules(self) -> list[dict]:
        rows = self._conn.execute("SELECT id FROM rules ORDER BY id").fetchall()
        return [state["rule"] for (row_id,) in rows for state in [self._state(row_id)] if state["status"] == "active"]

    def record_correction(self, record: dict, vendor: str, reviewer: str, rationale: str) -> dict:
        correction = {
            "correction_id": str(uuid.uuid4()),
            "record": checked_record(record),
            "vendor": required_text(vendor, "vendor"),
            "reviewer": required_text(reviewer, "reviewer"),
            "rationale": required_text(rationale, "rationale"),
            "created_at": _now(),
        }
        with self._tx():
            self._conn.execute(
                "INSERT INTO corrections (id, payload) VALUES (?, ?)",
                (correction["correction_id"], json.dumps(correction, ensure_ascii=False, allow_nan=False)),
            )
            self._event(CORRECTION_APPROVED, None, correction["reviewer"], correction)
        return _freeze(correction)

    def propose(self, correction_id: str) -> dict:
        correction_id = required_text(correction_id, "correction_id")
        with self._tx():
            row = self._conn.execute("SELECT payload FROM corrections WHERE id = ?", (correction_id,)).fetchone()
            if row is None:
                raise KeyError(f"unknown correction: {correction_id}")
            rule = candidate_from_correction(json.loads(row[0]), str(uuid.uuid4()))
            self._conn.execute(
                "INSERT INTO rules (id, correction_id, payload) VALUES (?, ?, ?)",
                (rule["rule_id"], correction_id, json.dumps(rule, ensure_ascii=False, allow_nan=False)),
            )
            self._event(RULE_PROPOSED, rule["rule_id"], rule["reviewer"], rule)
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
            self._event(RULE_VALIDATED, rule_id, reviewer, {"cases": cases, "report": report, "candidate": state["rule"]})
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
                raise ValueError(f"active rules changed since validation; revalidate rule: {rule_id}")
            if not stored["report"]["eligible"] or not fresh["eligible"]:
                raise ValueError(f"rule is not eligible for activation: {rule_id}")
            event = self._event(RULE_ACTIVATED, rule_id, reviewer, {"candidate": stored["candidate"], "report": fresh})
        return _freeze(event)

    def revoke(self, rule_id: str, reviewer: str, reason: str) -> dict:
        rule_id = required_text(rule_id, "rule_id")
        reviewer = required_text(reviewer, "reviewer")
        reason = required_text(reason, "reason")
        with self._tx():
            state = self._state(rule_id)
            if state["status"] != "active":
                raise ValueError(f"rule is not active: {rule_id}")
            event = self._event(RULE_REVOKED, rule_id, reviewer, {"reason": reason})
        return _freeze(event)

    def rules(self) -> list[dict]:
        rows = self._conn.execute("SELECT id FROM rules ORDER BY id").fetchall()
        return [
            {
                "rule": state["rule"],
                "status": state["status"],
                "validation": state["validation"]["data"]["report"] if state["validation"] else None,
                "activation": state["activation"],
            }
            for (row_id,) in rows
            for state in [self._state(row_id)]
        ]

    def history(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, rule_id, kind, reviewer, created_at, payload FROM events ORDER BY seq"
        ).fetchall()
        return [
            {"event_id": row[0], "kind": row[2], "rule_id": row[1], "reviewer": row[3], "created_at": row[4], "data": json.loads(row[5])}
            for row in rows
        ]

    def suggest(self, records: list[dict]) -> list[dict]:
        active = self._active_rules()
        return [
            {"record": record, **resolve(record, active)}
            for record in (checked_record(item) for item in records)
        ]
