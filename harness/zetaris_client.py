"""Client for a Zetaris instance — the federated read path for the close.

Zetaris is the AI Data Harness this repo's judgment queue reads through for
the Open Agent Hackathon wildcard entry: invoices, the bank feed and the GL
as separate sources answering one Lightning SQL, instead of one provider's
export. The instance runs on `snapflip-vultr` (docker compose bundle); this
client talks to its UI-proxy REST API over an SSH tunnel.

The contract mirrors the tested scripts in github.com/zetaris/getting-started
(`scripts/zetaris_sql.py`): `POST /sql-editor/sqls/run` carries one statement
and returns `{"data": rows}`; every request needs `X-Org-ID` and a fresh
`X-Request-ID`. JDBC (`jaydebeapi`, driver JAR from the bundle) is the second
channel and can be added here once the instance is up.

The honest limit, stated here because it belongs next to the code: this client
is structurally read-only. `run()` refuses anything whose first keyword is not
in `READ_VERBS` — the same stance as the Seapoint integration, where mutating
tools are never handed to the agent. Federation is for reading; the ledger's
write path stays exactly as governed as it was.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
import uuid
from typing import Any

DEFAULT_URL = "http://127.0.0.1:3300"  # SSH tunnel to the vultr install's UI
TIMEOUT_S = 60

READ_VERBS = {"select", "show", "describe", "desc", "explain", "with"}


class ZetarisUnavailable(RuntimeError):
    """The instance did not answer or is not configured."""


class ZetarisError(RuntimeError):
    """The instance answered with an error (HTTP or SQL)."""


def zetaris_available(timeout: float = 5) -> bool:
    """Whether a configured instance answers `SELECT 1`."""
    if not os.environ.get("ZETARIS_API_KEY"):
        return False
    try:
        ZetarisClient(timeout=timeout).run("SELECT 1", limit=1)
    except (ZetarisUnavailable, ZetarisError):
        return False
    return True


class ZetarisClient:
    """Read-only Lightning SQL over the UI-proxy REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        org_id: str | None = None,
        timeout: float = TIMEOUT_S,
    ):
        self.base_url = (
            base_url or os.environ.get("ZETARIS_REST_URL") or DEFAULT_URL
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("ZETARIS_API_KEY")
        self.org_id = org_id or os.environ.get("ZETARIS_ORG_ID", "1")
        self.timeout = timeout
        if not self.api_key:
            raise ZetarisUnavailable("ZETARIS_API_KEY is not set")

    def _call(self, path: str, body: dict | None = None) -> Any:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            method="POST" if body is not None else "GET",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "X-Org-ID": self.org_id,
                "X-Request-ID": str(uuid.uuid4()),
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            raise ZetarisError(f"{path}: HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise ZetarisUnavailable(f"{self.base_url}{path}: {exc}") from exc

    def run(self, sql: str, limit: int = 500) -> list[list]:
        """One statement, read verbs only — anything else is refused here."""
        verb = re.match(r"\s*(\w+)", sql or "")
        if not verb or verb.group(1).lower() not in READ_VERBS:
            raise ZetarisError(
                f"refused non-read statement: {(sql or '')[:40]!r} "
                f"(allowed: {', '.join(sorted(READ_VERBS))})"
            )
        out = self._call(
            "/sql-editor/sqls/run",
            {
                "queryId": str(uuid.uuid4()),
                "sql": sql,
                "source": "SqlEditor",
                "limit": limit,
            },
        )
        return out.get("data") or [] if isinstance(out, dict) else []

    def datasources(self) -> Any:
        return self._call("/datasource/datasources")
