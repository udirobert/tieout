"""Client for the H-MEM governed-memory sidecar.

`harness/hmem/` vendors the Meterless H-MEM engine (Apache-2.0) and serves it
over a small HTTP surface (`src/server.ts`, default `127.0.0.1:8737`). This
module is the only Python path into it, in the same way
`harness/exceptions.apply_decisions` is the only write path into a workbook:
callers never construct engine calls themselves.

Why a sidecar and not a port: the Meterless conformance runner loads a
TypeScript module and checks the spec's exact-tier contracts (ranking formula,
feedback deltas, sleep guardrails, dream approval boundary). Keeping the engine
in TypeScript keeps it conformance-testable; keeping this client thin keeps the
governance — tenant binding, the correction → propose → validate → activate
lifecycle — in `memory_store.py` where it already lives and is tested.

The honest limit, stated here because it belongs next to the code: the sidecar
is a localhost seam, not an authenticated service. Tenant isolation is
conventional (one engine instance per tenant, `tenant` required on every call),
not enforced. `available()` is how callers degrade cleanly — the agent must say
when memory is running on the legacy SQLite store, never pretend otherwise.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "http://127.0.0.1:8737"
TIMEOUT_S = 10


class HmemUnavailable(RuntimeError):
    """The sidecar did not answer. Callers decide whether to fall back."""


class HmemClient:
    """One tenant's handle on the H-MEM sidecar."""

    def __init__(
        self, tenant: str, base_url: str | None = None, timeout: float = TIMEOUT_S
    ):
        if not tenant or "/" in tenant or ".." in tenant:
            raise ValueError(f"invalid tenant {tenant!r}")
        self.tenant = tenant
        self.base_url = (
            base_url or os.environ.get("HMEM_SIDECAR_URL") or DEFAULT_URL
        ).rstrip("/")
        self.timeout = timeout

    def _call(self, method: str, path: str, body: dict | None = None) -> Any:
        payload: dict = dict(body or {})
        payload["tenant"] = self.tenant
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "x-tenant": self.tenant},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                out = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise HmemUnavailable(f"{self.base_url}{path}: {exc}") from exc
        if not out.get("ok"):
            raise RuntimeError(out.get("error", "hmem sidecar error"))
        return out["data"]

    def available(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/healthz", timeout=self.timeout
            ) as resp:
                return json.loads(resp.read().decode()).get("ok") is True
        except (urllib.error.URLError, OSError, ValueError):
            return False

    # Engine surface ------------------------------------------------------------

    def add(self, *, content: str, source: str, **fields: Any) -> dict:
        """A record with no `source` is rejected by the engine by construction."""
        return self._call(
            "POST",
            "/memory/add",
            {"input": {"content": content, "source": source, **fields}},
        )

    def query(self, query: str, **opts: Any) -> dict:
        return self._call("POST", "/memory/query", {"query": query, "opts": opts})

    def feedback(self, memory_id: str, kind: str) -> None:
        self._call("POST", "/memory/feedback", {"memoryId": memory_id, "kind": kind})

    def mine(self, event: str, text: str, **opts: Any) -> list[dict]:
        return self._call(
            "POST", "/memory/mine", {"event": event, "text": text, "opts": opts}
        )

    def all_memories(self) -> list[dict]:
        return self._call("GET", "/memory/all")

    def ledger(self) -> list[dict]:
        return self._call("GET", "/ledger")

    def ledger_stats(self) -> dict:
        return self._call("GET", "/ledger/stats")

    # Sleep cycle (preview-first consolidation) ---------------------------------

    def sleep_preview(self) -> dict:
        return self._call("POST", "/sleep/preview")

    def sleep_execute(self) -> dict:
        return self._call("POST", "/sleep/execute")

    def sleep_restore(self, backup_id: str) -> None:
        self._call("POST", "/sleep/restore", {"backupId": backup_id})

    # Dreaming (proposals materialize only on approval) -------------------------

    def dream_run(self) -> list[dict]:
        return self._call("POST", "/dream/run")

    def dream_pending(self) -> list[dict]:
        return self._call("GET", "/dream/pending")

    def dream_approve(self, proposal_id: str) -> dict | None:
        return self._call("POST", "/dream/approve", {"proposalId": proposal_id})

    def dream_reject(self, proposal_id: str) -> None:
        self._call("POST", "/dream/reject", {"proposalId": proposal_id})

    # Conflicts -----------------------------------------------------------------

    def conflicts_scan(self) -> list[dict]:
        return self._call("POST", "/conflicts/scan")

    def conflicts_queue(self) -> list[dict]:
        return self._call("GET", "/conflicts/queue")
