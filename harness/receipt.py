"""tieout receipt — per-task verification receipt.

Deterministic rules decide, LLM only narrates. Stored in trace + predictions status.
"""

import time


def build_task_receipt(
    task_id: str, verified: bool, evidence: str = "", reason: str = ""
) -> dict:
    return {
        "schemaVersion": 1,
        "receiptType": "tieout.task_receipt.v1",
        "taskId": task_id,
        "verified": bool(verified),
        "evidenceHash": evidence,
        "verdictReason": reason,
        "attestedAt": int(time.time()),
    }
