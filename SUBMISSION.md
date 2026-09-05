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
file (init workbook is the last-resort copy). When LibreOffice is present, we recalculate
and reject fatal formula errors (`#ERR!`, `#REF!`, `#NAME?`, `#VALUE!`, `#DIV/0!`);
missing-match tokens (`#N/A`) are handled under a generalized missing-lookup policy (e.g.
where outer lookups legitimately yield unresolved references for missing source entities,
such as unmatched school registers or entity lookups) to prevent false-positive fallbacks.
On the space-constrained Mac that check is skipped.

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
uv run evaluate.py --predictions /tmp/clone-run-400/predictions.jsonl --all --no-recalc --out results.json
```

```json
{
  "items": 400,
  "graded": 400,
  "missing": 0,
  "errors": 0,
  "pass_rate": 0.68,
  "cell_accuracy": 0.3709,
  "pass_rate_cell_level": 0.7382,
  "pass_rate_sheet_level": 0.552
}
```

### Ablation Progression

| Configuration | Pass Rate (Overall) | Cell Accuracy | Cell-Level Pass | Sheet-Level Pass | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| *WML Reference Target (arXiv:2607.20999)* | **74.67%** | — | — | — | Published SOTA on SpreadsheetBench Verified 400 |
| **Qwen3.8-27B Baseline (Values-first, no repair)** | **46.75%** (187/400) | 37.28% | 48.00% (132/275) | 44.00% (55/125) | /tmp/tinker-400, temp 0, 16k max_tokens |
| *+ Config-Parity Clone Run (Ship Candidate)* | **68.00%** (272/400) | **37.09%** | **73.82%** (203/275) | **55.20%** (69/125) | `/tmp/clone-run-400`: `qwen3_5` thinking on, official FORMAT_HINT, uncapped 120×30, our parse/write, no repair. +13.25pp vs old hybrid; +9pp vs official 59.0% floor. |
| *+ Codegen Execution Loop (Role A)* | **51.75%** (207/400) | **97.61%** | **43.64%** (120/275) | **69.60%** (87/125) | `/tmp/tinker-400-codegen` (`--path auto`). Sheet +25.6pp vs baseline. |
| *+ Hybrid Route (superseded)* | **54.75%** (219/400) | **95.45%** | **48.00%** (132/275) | **69.60%** (87/125) | `/tmp/tinker-400-hybrid`: thinking off. Harness-gap finding — same model, wrong decode path. |
| *+ Hybrid-v2 (pin-fix overlay, not ship)* | **52.75%** (211/400) | **95.44%** | **45.09%** (124/275) | **69.60%** (87/125) | `/tmp/tinker-400-hybrid-v2`: 27 cell-dip re-score, pin addresses-only, temp 0 n=1. 19/27 held; 8 regressions vs values-first. |
| *+ Hybrid-pin (scoped pin, not ship)* | **51.75%** (207/400) | **95.30%** | **43.64%** (120/275) | **69.60%** (87/125) | `/tmp/tinker-400-hybrid-pin`: 275 cells `--path values` temp 0 (init values kept) + codegen sheets. +14/−26 vs old hybrid cells. |
| *+ LoRA-v1 (not ship)* | **32.25%** (129/400) | **35.92%** | **46.55%** (128/275) | **0.80%** (1/125) | `/tmp/tinker-400-lora`. Data-mix starvation of codegen completions; overtrained on 202 records. |
| *+ Category Skills Library* | *pending eval* | | | | harness/skills.py |
| *+ Expert Iteration Fine-Tune (Role B)* | *post-mortem* | | | | LoRA-v1: 32.25% (data-mix starvation). **v2b**: 60/40 sheet:cell mix from 622 trajectories, 446 steps, lr 5e-5, rank 32. Fixed per-sample `out_path` race and epoch-iteration crash. Pre-fix step-200 artifact (~26% syntax drift) preserved in `data/sft/log_v2b/pre_fix_step200_artifact.json`. Did not overtake the 68.00% config-parity clone-run. Subsample evals of final + step-300 pending for the write-up. |

### Fine-tune post-mortem (Role B)

LoRA-v2b trained a 60/40 sheet:cell mix from 622 verifier-passed trajectories for 446 steps (lr 5e-5, rank 32). It fixed the per-sample `out_path` race and the epoch-iteration crash, and produced a clean 25-step checkpoint ladder. The pre-fix step-200 artifact (~26%, heavy syntax drift from JSON completions leaking into code generation) is preserved in `data/sft/log_v2b/pre_fix_step200_artifact.json` as the "before" evidence. Despite the corrected data mix and soft hyperparameters, the fine-tune could not overtake A's 68.00% config-parity clone-run; ship went to the non-fine-tuned run. C is archiving subsample evals of the v2b final and step-300 checkpoints for the write-up.

### Measurement variance (read before comparing rows)

A fresh temp-0 rerun of the identical values-first cell path (275 tasks) scored **43.64% vs the original 48.00%** — a −12 net-pass swing from re-running the same configuration. Temp-0 Tinker inference is not bit-reproducible, so task-level pass counts carry roughly **±3pp run-to-run variance**. Consequences for this table:

- Differences **smaller than ~2pp between rows are within noise**, not demonstrated improvements or regressions.
- Hybrid-pin's −3pp vs ship and Hybrid-v2's −2pp are consistent with "no measured effect," not proven harm; both were also *different samples* (new Tinker passes), not the same workbooks re-scored.
- Clone-run **68.00%** is **+13.25pp** over the old hybrid and **+9pp** over the official 59.0% floor — well outside the ±2–3pp noise band. It is the ship headline.
- Future promotion must beat **68.00%** by more than the noise band on the full 400.

## Your run on the 400

- `predictions.jsonl`: `/tmp/clone-run-400/predictions.jsonl`
- `outputs/`: `/tmp/clone-run-400/outputs/`
- `traces/`: `/tmp/clone-run-400/traces/`
- `run.log`: `/tmp/clone-run-400/run.log`
- parse audit: `/tmp/clone-run-400/parse_audit_summary.json` (33 JSONDecodeError, 25 truncated at 16k, 23 both; 365 harness-ok)

## Code

Pipeline in `harness/`, runs in Docker reading `/data` writing `/out`. Env vars:
`TINKER_API_KEY` (required), `GEMINI_API_KEY` (optional spare), `TINKER_PROJECT_ID`
(optional), `SOFFICE` (optional path to LibreOffice).

## Things to look at

- docs/TEAM-BRIEF.md — current roles
- docs/CONSTRAINTS.md — space + credits + scoring params
- docs/SETUP.md — venue setup order
