# Submission: tieout

## Team

- Team name: tieout
- Members, one GitHub handle per line:
- Repo URL: https://github.com/udirobert/tieout

## What we built and why

SpreadsheetBench Verified grades only answer cells after recalc; one wrong cell fails
the task. We built an execution-feedback harness around Tinker Qwen3.8-27B (thinking
off, 16k output tokens, temperature 0) rather than a larger one-shot prompt.

Cell-level tasks (275) stay values-first: serialize the workbook (fill-aware, answer
range pinned under the 20k cap), ask for JSON cell values, write with openpyxl, sanity
check, then attribution-guided repair (rejected reply + failure reason, smallest edit).
Sheet-level tasks (125) go code-first: the model writes openpyxl Python, which runs in
a temp-dir sandbox that never sees golden files, then we read back graded cells and
repair on exec/stderr. Each path falls back to the other; we never ship a missing
file (init workbook is the last-resort copy). When LibreOffice is present we recalc
and reject `#ERR!` values; on the space-constrained Mac that check is skipped.

We did not put the 400 goldens in any training set. Fine-tune (if shipped) will be
expert-iteration on verifier-passing trajectories only — details in Models once a
checkpoint exists. Docker image still to freeze.

## Models

- Inference: `Qwen/Qwen3.8-27B` via Tinker (`TINKER_API_KEY`). Optional spare:
  Gemini 3.7 Flash (`GEMINI_API_KEY`). No OpenRouter.
- Fine-tune: none yet. If added: `tinker://<run-id>/sampler_weights/final` + base
  model, training mix, whether goldens were in it, steps/LR/compute/wall time.

## Scores on the 400

```sh
uv run evaluate.py --predictions /tmp/tinker-400/predictions.jsonl --all --no-recalc --out results.json
```

```json
{
  "items": 400,
  "graded": 400,
  "missing": 0,
  "errors": 0,
  "pass_rate": 0.4675,
  "cell_accuracy": 0.3728,
  "pass_rate_cell_level": 0.48,
  "pass_rate_sheet_level": 0.44
}
```

### Ablation Progression

| Configuration | Pass Rate (Overall) | Cell Accuracy | Cell-Level Pass | Sheet-Level Pass | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Qwen3.8-27B Baseline (Values-first, no repair)** | **46.75%** (187/400) | 37.28% | 48.00% (132/275) | 44.00% (55/125) | /tmp/tinker-400, temp 0, 16k max_tokens |
| *+ Attribution-guided Repair (v1)* | *pending eval* | | | | committed in 93d109c |
| *+ Category Skills Library* | *pending eval* | | | | harness/skills.py → codegen system prompt |
| *+ Codegen Execution Loop (Role A)* | **51.75%** (207/400) | **97.61%** | **43.64%** (120/275) | **69.60%** (87/125) | `/tmp/tinker-400-codegen` (`--path auto` with fallbacks). Cell drop from codegen fallback. |
| *+ Hybrid route (ship)* | **54.75%** (219/400) | **95.45%** | **48.00%** (132/275) | **69.60%** (87/125) | `/tmp/tinker-400-hybrid`: cell←values-first, sheet←codegen. No new model calls. Default `--path hybrid`. |
| *+ Expert Iteration Fine-Tune (Role B)* | *pending eval* | | | | Tinker LoRA checkpoint |

## Your run on the 400

- `predictions.jsonl`: `/tmp/tinker-400-hybrid/predictions.jsonl`
- `outputs/`: `/tmp/tinker-400-hybrid/outputs/`
- `traces/`: `/tmp/tinker-400-hybrid/traces/`
- `run.log`: `/tmp/tinker-400-hybrid/run.log`

## Code

Pipeline in `harness/`, runs in Docker reading `/data` writing `/out`. Env vars:
`TINKER_API_KEY` (required), `GEMINI_API_KEY` (optional spare), `TINKER_PROJECT_ID`
(optional), `SOFFICE` (optional path to LibreOffice).

## Things to look at

- docs/TEAM-BRIEF.md — current roles
- docs/CONSTRAINTS.md — space + credits + scoring params
- docs/SETUP.md — venue setup order
