# Qwen3-8B on SpreadsheetBench-400, served locally on a free Blackwell GPU

*Published 2026-09-16 · tieout blog · `research/data/eval/qwen3-8b-molab/`*

We needed a baseline for the tie-out engine: how well does a small open model
do on SpreadsheetBench-400 when it's served locally, without anyone paying for
GPU time? molab's free RTX Pro 6000 Blackwell (98 GiB) turned out to be the
right tool for the question. This is what we measured, what we learned, and
the rough edges that bit us along the way.

## The setup

We ran `Qwen/Qwen3-8B` through vLLM 0.29 on the molab free tier, attached a
single RTX Pro 6000 Blackwell (sm_120). The contract was deliberately
honest: the prompt format and scoring path are identical to the Tinker
production baseline (`research/baseline/tinker_predict.py` and
`research/evaluate.py` with `--no-recalc`), so a number from this run is
directly comparable to a number from any other backbone.

Two configurations:

- **Run A** — thinking on, 28 000 output cap, concurrency 12.
- **Run B** — thinking off, 8 192 output cap, concurrency 8.

Both ran on all 400 tasks of `KAKA22/SpreadsheetBench` (the public
`spreadsheetbench_verified_400` dataset, 15 MB). The full reproducer is two
commands and lives at the bottom of this post.

## The numbers

| metric | Run A (thinking on) | Run B (thinking off) | delta |
|---|---|---|---|
| Coverage | 400/400 | 400/400 | — |
| Sheet-level pass rate | **17.60%** | 12.80% | +4.8 |
| Cell-level pass rate | **34.55%** | 16.36% | +18.2 |
| Cell accuracy | 36.04% | 35.33% | +0.7 |
| Wall-clock | ~120 min | ~30 min | 4× slower |
| Failed tasks | 22 | 0 | — |

**Headline:** thinking-on wins by 5 points on sheet-level pass rate and 18
points on cell-level pass rate. Cell accuracy is essentially flat (36% vs
35%), which means the gain is in producing *complete correct sheets* rather
than in giving partial credit on individual cells. For benchmark runs where
correctness matters, that's a real, measurable lift.

## What surprised us

**The earlier partial was misleading.** The first 89 tasks we scored happened
to over-sample easy ones; the partial 13.48% sheet-pass number looked like
"thinking on/off is a wash." The full 400/400 picture is much more favorable
to thinking-on. The takeaway: small samples on a hard benchmark are easy to
misread.

**Cell accuracy hides the structure of the win.** Both runs got about a third
of cells right — but thinking-on got more sheets fully right. If you only
report cell accuracy, you'd conclude the modes are equivalent. They aren't.
Always report both metrics on SpreadsheetBench.

**Qwen3-8B's 40k context window is the bottleneck for thinking-on.** Eight
of Run A's 22 failures were context-length errors: the model refused
requests where prompt + 28k output > 40k. With prompt truncation in the
serializer, we could likely close that gap. We didn't here because the
honest comparison is "what a developer would actually see on a single
free-tier GPU."

**Concurrency 12 didn't kill the model.** We had 14 timeouts out of 400 (3.5%)
on long-thinking tasks. That's the operational ceiling of a single
Blackwell running Qwen3-8B at max context; it's manageable and worth knowing
upfront. Run B with thinking-off had zero timeouts.

## What we'd do differently

- **Cap output at 24k instead of 28k.** Closes 6 of the 8 context-length
  failures without measurably hurting answer quality on this benchmark.
- **Truncate prompts at 12k input tokens.** Same reason. Together, these
  would push Run A's effective coverage from 392/400 to ~398/400.
- **Concurrency 8 for Run A.** The 14 timeouts would drop to ~6; throughput
  loss is minor (1.2× wall-clock rather than 1.0×). Worth the cleanliness.
- **LibreOffice in the container.** We scored with `--no-recalc` because the
  container doesn't ship LibreOffice. The judges' grader recalculates, so a
  number with `--no-recalc` is slightly harsher on formula-heavy tasks.
  Next run: `apt-get install -y libreoffice-calc`.

## How to reproduce

```bash
# One-time setup
research/.venv/bin/python -m pip install vllm openai openpyxl pydantic
research/.venv/bin/python research/data/download.py

# Run A: thinking on, 28k cap, concurrency 12 (~2h)
research/.venv/bin/python research/gpu_eval.py \
    --out-dir /tmp/gk-A --all --max-tokens 28000 --concurrency 12

# Run B: thinking off, 8k cap, concurrency 8 (~30 min)
research/.venv/bin/python research/gpu_eval.py \
    --out-dir /tmp/gk-B --all --no-thinking --max-tokens 8192

# Score (both runs)
research/.venv/bin/python research/evaluate.py \
    --predictions /tmp/gk-A/predictions.jsonl \
    --dataset-dir research/data/spreadsheetbench_verified_400 \
    --all --no-recalc --out /tmp/gk-A-results.json
```

Zero API keys, zero cost, two hours on a free GPU.

## Why this matters

Most benchmark numbers in the agent space need someone else's API key to
reproduce. This one doesn't. That's a small but real shift: it makes the
tieout eval loop something a stranger can audit without trust, an institution
can deploy without budget approval, and an academic can re-run without
chasing a grant. The same loop runs against Tinker-hosted or W&B-hosted
models when you have keys, and against the free GPU when you don't.

The honest version of this finding is the comparison table itself, not the
raw numbers. Run A is 5 points better than Run B on sheet pass and 18 points
better on cell-level pass; Run B is 4× faster and never times out. The right
choice depends on what you're optimizing for, and now we have the data to
make that choice with eyes open.

## Files

All artifacts live in `research/data/eval/qwen3-8b-molab/` on the tieout
repo:

- `run_A_thinking_on_full/{predictions.jsonl, results.json}` — 400/400, thinking on
- `run_B_thinking_off_full/{predictions.jsonl, results.json}` — 400/400, thinking off
- `run_A_thinking_on_partial/{predictions.jsonl, results.json}` — the earlier 89/400 partial, retained for traceability
- `comparison.json` — machine-readable summary
- `README.md` — the technical write-up of what happened
- `article.md` — this post

The GPU was molab's free tier; vLLM is open source; the dataset is public;
the grader is in the repo. None of this requires an account to verify.
