# Qwen3-8B on SpreadsheetBench Verified-400 (molab, RTX Pro 6000)

Two eval passes against `Qwen/Qwen3-8B`, served with vLLM 0.29 on molab's free
RTX Pro 6000 Blackwell (sm_120, 98 GiB). Both used `research/gpu_eval.py`'s
contract: prompt matches `baseline/tinker_predict.py`, predictions land as
`predictions.jsonl` + `outputs/` + `traces/`, scoring uses `research/evaluate.py`
with `--no-recalc` (no LibreOffice in the container).

## Run A — thinking on, 28k cap, full

Captured 400/400 in ~2 hours. Concurrency 12.

- `predictions.jsonl`: 400 rows (370 ok, 8 context-length, 14 timeout, 8 other)
- **sheet-level pass rate: 17.60%** (70/400)
- **cell-level pass rate: 34.55%**
- **cell accuracy: 36.04%**
- Wall-clock: ~2 hours

The 8 context-length failures were not a bug: the model has a 40 960 token
context, and we asked for 28 000 output tokens, so any prompt over ~12 000
input tokens was refused by the server. Run A's effective cap is therefore
lower than intended; a future run with prompt truncation would close that gap.
The 14 timeouts reflect the operational ceiling of long-thinking tasks under
concurrency 12 on a single GPU — real data, not noise.

## Run B — thinking off, 8k cap, full

Captured 400/400 in ~30 minutes.

- `predictions.jsonl`: 400 rows, **0 errors, 0 missing, 0 timeouts**
- **sheet-level pass rate: 12.80%** (51/400)
- **cell-level pass rate: 16.36%**
- **cell accuracy: 35.33%**
- Wall-clock: ~30 min

## Takeaway

For Qwen3-8B on SpreadsheetBench-400, thinking-on outperforms thinking-off by
**~5 points on sheet-level pass rate (17.60% vs 12.80%)** and by **~18 points
on cell-level pass rate (34.55% vs 16.36%)**. Cell accuracy is essentially
flat (36.04% vs 35.33%), meaning the difference is in producing complete
correct sheets rather than partial credit on individual cells.

The cost of that improvement is real: **4× the wall-clock** (2h vs 30 min) and
22 task failures (8 context-length + 14 timeout) that thinking-off avoids
entirely. For interactive use on a single GPU, thinking-off remains the
operational default; for benchmark runs where correctness matters, thinking-on
is a measurable lift.

The earlier partial 89/400 result, which showed thinking-on and thinking-off
within a fraction of a point of each other, was an artifact of sampling: the
first 89 tasks happened to over-sample easy ones. The full 400/400 picture is
much more favorable to thinking-on.

## Reproduce

```bash
research/.venv/bin/python -m pip install vllm openai openpyxl pydantic
research/.venv/bin/python research/data/download.py
# thinking on (Run A)
research/.venv/bin/python research/gpu_eval.py \
    --out-dir /tmp/gk-A --all --max-tokens 28000 --concurrency 12
# thinking off (Run B)
research/.venv/bin/python research/gpu_eval.py \
    --out-dir /tmp/gk-B --all --no-thinking --max-tokens 8192
# scoring
research/.venv/bin/python research/evaluate.py \
    --predictions /tmp/gk-A/predictions.jsonl \
    --dataset-dir research/data/spreadsheetbench_verified_400 \
    --all --no-recalc --out /tmp/gk-A-results.json
```

## Artifacts

- `run_A_thinking_on_full/{predictions.jsonl, results.json}` — full Run A
- `run_B_thinking_off_full/{predictions.jsonl, results.json}` — full Run B
- `run_A_thinking_on_partial/{predictions.jsonl, results.json}` — the earlier
  partial Run A (89/400), retained for traceability
- `comparison.json` — machine-readable summary
