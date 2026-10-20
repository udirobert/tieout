"""Governed write-back to Seapoint — the single, recorded path by which the agent
may change ledger data.

The raw Seapoint mutating tools (`set_transaction_category`, `set_transaction_coding`,
`set_transaction_vendor`, `update_vendor`, `approve_reconciliation`) are NEVER handed
to the model. `assemble_tools()` holds them back and exposes only the wrappers below.
Each wrapper:

  - refuses to act without `confirm=true` (preview-first),
  - refuses a confirmed write with no `evidence` (why this change is justified),
  - returns Seapoint's own audit record — the `previous_*` value(s) and the
    `change_id` into Seapoint's change log.

So it is structurally impossible for the agent to mutate the ledger except through a
confirmed, evidenced, logged step. "Blank is an answer" becomes an architecture, not
a prompt rule — which is the whole point: an agent a finance team can let near a
ledger because the audit trail is in the write path, not bolted on after.

Build the tool list with `governed_write_tools(client, available_raw_names)`, where
`client` is the live Strands `MCPClient` and `available_raw_names` is the set of raw
Seapoint tool names actually exposed to this workspace.
"""

from __future__ import annotations

import json
import uuid

# Raw Seapoint tool names this module governs. A write tool not in a workspace's
# surface simply yields no wrapper (the capability is absent, not faked).
CATEGORY_TOOL = "set_transaction_category"
CODING_TOOL = "set_transaction_coding"
VENDOR_TOOL = "set_transaction_vendor"
APPROVE_TOOL = "approve_reconciliation"


def _result_text(result) -> str:
    """Render an MCPToolResult as readable text, preserving Seapoint's audit fields."""
    status = getattr(result, "status", "?")
    content = getattr(result, "content", None) or []
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            parts.append(block.get("text") or json.dumps(block, default=str))
        else:
            parts.append(getattr(block, "text", None) or str(block))
    return f"[{status}] " + "\n".join(parts)


def _invoke(client, raw_name: str, arguments: dict) -> str:
    """Call a held Seapoint write tool directly on the MCP session."""
    result = client.call_tool_sync(f"ck-{uuid.uuid4().hex[:12]}", raw_name, arguments)
    return _result_text(result)


def governed_write_tools(client, available: set[str]) -> list:
    """Return the governed Seapoint write tools whose raw tool this workspace exposes.

    Closures capture `client` (to invoke the held raw tool) and `available` (to refuse
    a capability the workspace doesn't grant). Nothing here exposes a raw mutating tool.
    """
    from strands import tool

    def _guard(raw_name: str, confirm: bool, evidence: str, preview: str) -> str | None:
        if raw_name not in available:
            return f"unavailable: this Seapoint workspace did not expose `{raw_name}`."
        if not confirm:
            return "PREVIEW (nothing changed). " + preview + " Re-call with confirm=true to apply."
        if not (evidence or "").strip():
            return "REFUSED: provide `evidence` (why this change is correct) before confirming a ledger write."
        return None

    @tool
    def seapoint_set_category(
        transaction_ids: list, category_id: str, evidence: str = "", confirm: bool = False
    ) -> str:
        """Govern a Seapoint category change — the ONLY way to set a transaction's category.

        Preview-first: call once to preview, then again with confirm=true to apply.
        A confirmed write requires `evidence`. Seapoint returns `previous_category_id`
        and a `change_id` per row — surface them to the human as the audit record.

        Args:
            transaction_ids: ids from seapoint_query_transactions (<=50, one org)
            category_id: target category id from seapoint_query_categories
            evidence: why this category is correct (required to confirm)
            confirm: false previews; true applies the change
        """
        blocked = _guard(
            CATEGORY_TOOL, confirm, evidence,
            f"Will set category_id={category_id} on {len(transaction_ids)} transaction(s): "
            f"{transaction_ids}. Evidence: {evidence or '(none)'}.",
        )
        if blocked is not None:
            return blocked
        return _invoke(client, CATEGORY_TOOL, {"transaction_ids": transaction_ids, "category_id": category_id})

    @tool
    def seapoint_set_coding(
        transaction_ids: list,
        account_code: str = "",
        tax_rate_code: str = "",
        evidence: str = "",
        confirm: bool = False,
    ) -> str:
        """Govern a Seapoint bookkeeping-coding change (account code / tax rate).

        Setting both codes moves a transaction to `awaiting_approval`, ready for
        seapoint_approve_reconciliation. Preview-first; confirmed writes require
        `evidence`. Returns codes before/after and the reconciliation status.

        Args:
            transaction_ids: ids from seapoint_query_transactions (<=50, one org)
            account_code: chart-of-accounts code (omit to keep each txn's own)
            tax_rate_code: tax rate code (omit to keep each txn's own)
            evidence: why this coding is correct (required to confirm)
            confirm: false previews; true applies the change
        """
        if not account_code and not tax_rate_code:
            return "REFUSED: give at least one of account_code or tax_rate_code."
        args: dict = {"transaction_ids": transaction_ids}
        if account_code:
            args["account_code"] = account_code
        if tax_rate_code:
            args["tax_rate_code"] = tax_rate_code
        blocked = _guard(
            CODING_TOOL, confirm, evidence,
            f"Will set {', '.join(f'{k}={v}' for k, v in args.items() if k != 'transaction_ids')} "
            f"on {len(transaction_ids)} transaction(s): {transaction_ids}. Evidence: {evidence or '(none)'}.",
        )
        if blocked is not None:
            return blocked
        return _invoke(client, CODING_TOOL, args)

    @tool
    def seapoint_set_vendor(
        transaction_ids: list, vendor_id: str, evidence: str = "", confirm: bool = False
    ) -> str:
        """Govern a Seapoint vendor (participant) reassignment.

        Moving a transaction can change its inherited category too; Seapoint returns
        the category before/after and a `change_id`. Preview-first; confirmed writes
        require `evidence`.

        Args:
            transaction_ids: ids from seapoint_query_transactions (<=50, one org)
            vendor_id: participant id from seapoint_query_transaction_participants
            evidence: why this vendor is correct (required to confirm)
            confirm: false previews; true applies the change
        """
        blocked = _guard(
            VENDOR_TOOL, confirm, evidence,
            f"Will move {len(transaction_ids)} transaction(s) to vendor_id={vendor_id}: "
            f"{transaction_ids}. Evidence: {evidence or '(none)'}.",
        )
        if blocked is not None:
            return blocked
        return _invoke(client, VENDOR_TOOL, {"transaction_ids": transaction_ids, "vendor_id": vendor_id})

    @tool
    def seapoint_approve_reconciliation(
        transaction_ids: list, evidence: str = "", confirm: bool = False
    ) -> str:
        """Govern Seapoint reconciliation approval — the final sign-off on coded transactions.

        Only approve what a human has decided. Preview-first; confirmed approvals
        require `evidence`.

        Args:
            transaction_ids: ids of awaiting_approval transactions (<=50, one org)
            evidence: the human decision authorising approval (required to confirm)
            confirm: false previews; true approves
        """
        blocked = _guard(
            APPROVE_TOOL, confirm, evidence,
            f"Will APPROVE reconciliation for {len(transaction_ids)} transaction(s): "
            f"{transaction_ids}. Evidence: {evidence or '(none)'}.",
        )
        if blocked is not None:
            return blocked
        return _invoke(client, APPROVE_TOOL, {"transaction_ids": transaction_ids})

    candidates = {
        CATEGORY_TOOL: seapoint_set_category,
        CODING_TOOL: seapoint_set_coding,
        VENDOR_TOOL: seapoint_set_vendor,
        APPROVE_TOOL: seapoint_approve_reconciliation,
    }
    # Expose a governed wrapper only when its raw tool is actually available.
    return [fn for raw, fn in candidates.items() if raw in available]
