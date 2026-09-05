"""tieout tracer — trace format judges actually read.

One file per task: traces/<id>.jsonl, one line per model call in order.
Mirrors upstream baseline/common.py predict_task trace keys, plus agent tool fields.
A trace with the golden value and no reasoning, a prompt containing golden values,
or a lookup step = disqualification. Keep failed calls with error set.
"""

TRACE_FIELDS = (
    "step,model,prompt,response,input_tokens,output_tokens,latency_ms,error,"
    "tool,tool_input,tool_output"
)

# Truncate workbook serialization to 20k chars per SUBMISSION.md, and say so in SUBMISSION.md.
MAX_WORKBOOK_CHARS = 20000
