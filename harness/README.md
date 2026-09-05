# harness — tieout pipeline (scaffold, no deps installed here)

`classify -> write python -> exec -> verify second way -> retry <=3 -> write workbook`

Upstream reference: `../research/baseline/common.py` (prompt, answer schema, output files),
`../research/sb.py` (answer cells, ranges, serialization), `../research/baseline/llm_predict.py`.

## Files (skeletons + contracts committed at hack start; implementations land today)

- `pipeline.py` — entry: `--dataset-dir /data --out-dir /out`. One line per task in
  `predictions.jsonl` (`{"id","output":"outputs/<id>.xlsx","status":"ok|error"}`).
  On failure still write line + copy init workbook as output (missing = 0).
- `prompts.py` — task-type prompts (reason hard, direct easy).
  System: spreadsheet expert, compute FINAL VALUES for answer range, plain values not formulas
  for v0; formulas with `_xlfn.` prefix for v1 where scorer recalcs.
- `executor.py` — runs model-written openpyxl code INSIDE container only. Timeout per task,
  captures stderr into trace `tool_output`. No host paths, no --privileged.
- `verifier.py` — re-reads written workbook (`data_only` + formula pass), checks agreement.
  Numbers 2dp, dates as serials, "" == empty (match scorer normalization).
- `tracer.py` — `traces/<id>.jsonl`, one line per model call in order:
  `{step,model,prompt,response,input_tokens,output_tokens,latency_ms,error,tool,tool_input,tool_output}`.
  Truncate workbook serialization to 20k chars. Never include golden values in prompts.

Greedy decode / temperature 0 where API allows. Model ids fixed in code. Keys via env only.
Sampling nondeterminism (±few tasks between runs) is expected — report shipped-evaluator numbers.
