"""tieout tracer — traces/<id>.jsonl, one line per model call, in order.

Never include golden values in prompts; keep failed calls with error set
(golden value with no reasoning = disqualification).
"""

import json
from pathlib import Path


FIELDS = (
    "step",
    "model",
    "prompt",
    "response",
    "input_tokens",
    "output_tokens",
    "latency_ms",
    "error",
    "tool",
    "tool_input",
    "tool_output",
)


def append_trace(out_dir, task_id: str, record: dict) -> None:
    rec = {k: record.get(k) for k in FIELDS}
    with (Path(out_dir) / "traces" / f"{task_id}.jsonl").open(
        "a", encoding="utf-8"
    ) as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
