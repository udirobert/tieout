"""tieout executor — runs model-written openpyxl code INSIDE the container only.

Venue-only execution. This file is a stub until Sat 12:00; no deps installed here.
Rules: timeout per task, capture stderr into trace tool_output, no host paths,
no --privileged, no network. On any failure caller copies init workbook as output.
"""

TIMEOUT_S = 120
ALLOWED_IMPORTS = ("openpyxl", "datetime", "math", "json", "re", "statistics")


def run_snippet(code: str, task_id: str) -> dict:
    """Run model-written snippet in-process (container). Returns {ok, stdout, error}.

    Real implementation at venue: subprocess with timeout, stdout cap 4000 chars,
    SUMMARY_JSON last-line parse, positive control (known-answer check
    must pass or verdict is inconclusive, never forced pass).
    """
    raise NotImplementedError("venue: implement subprocess run with TIMEOUT_S")
