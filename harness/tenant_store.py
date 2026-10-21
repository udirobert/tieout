"""Tenant-bound SQLite stores.

Both the governed-memory store and the decision ledger are SQLite files that
belong to exactly one tenant. This module holds the parts they share:

* opening the file with `0600` and refusing a missing parent directory,
* the `meta` table that records which tenant the file belongs to,
* the rule that the bound tenant is set once and then locked, and
* the helpers that check a record's scope against it.

**One file per tenant.** A file is bound to one tenant the first time it is
written to and stays bound: reopening it under a different tenant raises
`TenantMismatch` rather than silently serving another customer's rows. That
choice makes the retention, deletion, and export policy a filesystem operation
instead of a `WHERE` clause someone has to remember — which is what
`docs/COREWEAVE.md` asks for before real customer data exists.

Files written before this existed have no bound tenant. They open unbound, tag
every row with the scope tenant of its payload, and bind on their first write.
The migration backfills the `tenant` column from the stored payload so old
files stay readable.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from tenant import CrossTenantWrite, TenantMismatch, tenant_of_scope

META_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

TENANT_KEY = "tenant"


class TenantStore:
    """A SQLite file bound to one tenant.

    Subclasses provide `SCHEMA` (their own tables) and call `_init_schema`.
    """

    SCHEMA = ""

    def __init__(self, path: Path, tenant: str | None = None):
        path = Path(path)
        if not path.parent.is_dir():
            raise FileNotFoundError(f"database directory does not exist: {path.parent}")
        try:
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600))
        except FileExistsError:
            pass
        self._conn = sqlite3.connect(str(path), isolation_level=None)
        self._path = path
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA busy_timeout = 5000")
            self._conn.executescript(META_SCHEMA)
            self._conn.executescript(self.SCHEMA)
            self._migrate()
            self._tenant = self._resolve_tenant(tenant)
        except BaseException:
            self._conn.close()
            raise

    # -- lifecycle -------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self) -> None:
        self._conn.close()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def tenant(self) -> str | None:
        """The tenant this file belongs to, or None while it is still unbound."""
        return self._tenant

    # -- tenant binding --------------------------------------------------

    def _resolve_tenant(self, requested: str | None) -> str | None:
        stored = self._meta_get(TENANT_KEY)
        if stored and requested and stored != requested:
            raise TenantMismatch(
                f"{self._path} belongs to tenant {stored!r}, not {requested!r}"
            )
        if stored:
            return stored
        if requested:
            self._meta_set(TENANT_KEY, requested)
            return requested
        return None

    def _bind_tenant(self, scope: dict) -> str:
        """Bind an unbound file to the scope tenant of its first write."""
        scope_tenant = tenant_of_scope(scope)
        if self._tenant is None:
            self._meta_set(TENANT_KEY, scope_tenant)
            self._tenant = scope_tenant
            return scope_tenant
        if scope_tenant != self._tenant:
            raise CrossTenantWrite(
                f"tenant {scope_tenant!r} cannot write to the store for "
                f"{self._tenant!r}"
            )
        return scope_tenant

    def _check_scope(self, scope: dict) -> str:
        """Reject a write whose scope names another tenant."""
        scope_tenant = tenant_of_scope(scope)
        if self._tenant is not None and scope_tenant != self._tenant:
            raise CrossTenantWrite(
                f"tenant {scope_tenant!r} cannot write to the store for "
                f"{self._tenant!r}"
            )
        return scope_tenant

    def _visible(self, row_tenant: str | None) -> bool:
        """Whether a stored row belongs to a tenant this store may return."""
        if self._tenant is None:
            return True
        return row_tenant == self._tenant

    # -- meta ------------------------------------------------------------

    def _meta_get(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    def _meta_set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    # -- schema migration ------------------------------------------------

    def _columns(self, table: str) -> set[str]:
        rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row[1] for row in rows}

    def _add_column(self, table: str, column: str, decl: str) -> None:
        if column in self._columns(table):
            return
        self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def _migrate(self) -> None:
        """Bring a file written before tenant binding up to the current shape.

        The `tenant` column is added to every row table and backfilled from the
        payload each row already carries, so old files keep working and old
        rows keep their identity.
        """
        for table in self.TENANT_TABLES:
            self._add_column(table, "tenant", "TEXT NOT NULL DEFAULT ''")
        if not any(self._columns(t) & {"tenant"} for t in self.TENANT_TABLES):
            return
        self._backfill_tenants()

    def _backfill_tenants(self) -> None:
        """Fill empty `tenant` columns from the scope inside each payload.

        Subclasses with tables whose payload does not carry the scope (an event
        points at a rule rather than embedding it) override this.
        """
        for table in self.TENANT_TABLES:
            for row_id, payload_text in self._row_tenants(table):
                tenant = self._payload_tenant(payload_text)
                if tenant:
                    self._set_row_tenant(table, row_id, tenant)

    def _row_tenants(self, table: str) -> list[tuple[str, str]]:
        """(id, payload) rows of a table, for backfilling."""
        rows = self._conn.execute(
            f"SELECT id, payload FROM {table} WHERE tenant = '' OR tenant IS NULL"
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    @staticmethod
    def _payload_tenant(payload_text: str) -> str | None:
        try:
            payload = json.loads(payload_text)
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        scope = payload.get("scope")
        if isinstance(scope, dict) and scope.get("tenant"):
            return str(scope["tenant"])
        record = payload.get("record")
        if isinstance(record, dict):
            scope = record.get("scope")
            if isinstance(scope, dict) and scope.get("tenant"):
                return str(scope["tenant"])
        return None

    def _set_row_tenant(self, table: str, row_id: str, tenant: str) -> None:
        self._conn.execute(
            f"UPDATE {table} SET tenant = ? WHERE id = ?", (tenant, row_id)
        )
