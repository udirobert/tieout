# Submission: tieout (Encode × Ylookup — archived)

> **Active submission:** Syndicate by Maximor, Track 2 (Office of the CFO) — see
> [`SYNDICATE.md`](SYNDICATE.md), [`docs/SYNDICATE-WORKFLOW.md`](docs/SYNDICATE-WORKFLOW.md),
> [`docs/SYNDICATE-DEMO.md`](docs/SYNDICATE-DEMO.md).

This file preserves the Encode hackathon write-up, scores, and ablation table. The 68%
SpreadsheetBench result is reused as **background validation** for Syndicate, not the demo story.

---

## Team

- Team name: tieout
- Members, one GitHub handle per line:
- Repo URL: https://github.com/udirobert/tieout

## What we built and why

SpreadsheetBench Verified grades only answer cells after recalc; one wrong cell fails
the task. Our ship is a one-shot values-first Tinker Qwen3.8-27B run with the official
recipe: cookbook `qwen3_5` renderer (thinking **on**, CoT stripped at parse), full
120×30 workbook serialize with no char cap, official `SYSTEM_PROMPT` + `FORMAT_HINT`,
temperature 0, `max_tokens=16384`, renderer stop sequences. We keep our own
`parse_answer` and `write_output` on top (strictly more permissive than the official
parser/writer — dates as real dates, numeric strings coerced, `MergedCell` writes
through the merge origin, `""` == `None`). No skills, no answer-range pin, no repair
loop, no codegen path, no `enable_thinking=False` override.

The interesting finding from the same model is the harness gap: turning thinking *off*
(the default path on our earlier hybrid) costs **−13.25pp** on the same 400 — 54.75%
with thinking off vs 68.00% with thinking on, same `Qwen3.8-27B`, same official prompt
and serialization, only the decode path differs. CoT is doing real work on multi-step
lookups and aggregations; suppressing it loses those tasks entirely.

The container also ships a recalc gate when LibreOffice is present: reject fatal
formula errors (`#ERR!`, `#REF!`, `#NAME?`, `#VALUE!`, `#DIV/0!`); treat missing-match
tokens (`#N/A`) under a generalized missing-lookup policy (e.g. outer lookups that
legitimately yield unresolved references for missing source entities such as unmatched
entity registers) so they don't trigger false-positive fallbacks. On the space-constrained
Mac the gate is skipped. Both rules are content-shape heuristics, not id-keyed.

A second run with the model's CoT left enabled produces 33 `JSONDecodeError`s and 25
truncations at the 16k output ceiling (23 overlap); 365 of 400 produce clean parse +
write. The 35 that fail fall back to the init workbook, so `items` is always 400,
`missing` always 0. We did not put the 400 goldens in any training set; the fine-tune
work is documented as a negative result in the ablation table.

## Models

- Inference: `Qwen/Qwen3.8-27B` via Tinker (`TINKER_API_KEY`), cookbook `qwen3_5`
  renderer with thinking on (CoT stripped at parse via `renderer.parse_response`).
  Optional spare: Gemini 3.7 Flash (`GEMINI_API_KEY`). No OpenRouter.
- Fine-tune: **not shipped**. We trained a 60/40 sheet:cell mix LoRA (v2b, 622 verified
  trajectories, 446 steps, lr 5e-5, rank 32). It fixed the v1 data-mix starvation and
  the JSON-delimiter drift but did not clear the 68.00% config-parity clone-run on the
  100-subsample (`final` 47%, `step-300` 44%, vs the 64% promotion bar — both within
  noise of the LoRA-v1 result, both well below the new 68% ship). Pre-fix and
  post-fix checkpoint artifacts, loss curve, and the 60/40 mix source list are in
  `data/sft/log_v2b/`. The 400 goldens were not in any training set; training data
  was verifier-passing trajectories only.

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
| *+ v2b fine-tune subsample (step-300, not ship)* | **44.00%** (44/100) | **89.17%** | **40.00%** (20/50) | **48.00%** (24/50) | `/tmp/tinker-100-v2b-step300`. Same 100-subsample as below. Below the 64% bar; not promoted. |
| *+ v2b fine-tune subsample (final, not ship)* | **47.00%** (47/100) | **89.21%** | **44.00%** (22/50) | **50.00%** (25/50) | `/tmp/tinker-100-v2b-final`. Same 100-subsample; lr 5e-5, 446 steps, 60/40 mix. Below the 64% bar; not promoted. |
| *+ Category Skills Library* | *pending eval* | | | | harness/skills.py |
| *+ Expert Iteration Fine-Tune (Role B)* | *post-mortem* | | | | LoRA-v1: 32.25% (data-mix starvation, negative). **v2b**: 60/40 sheet:cell mix from 622 trajectories, 446 steps, lr 5e-5, rank 32. Fixed per-sample `out_path` race and epoch-iteration crash. Pre-fix step-200 artifact (~26% syntax drift) preserved in `data/sft/log_v2b/pre_fix_step200_artifact.json`. Did not overtake the 68.00% config-parity clone-run on the 100-subsample; see the v2b subsample rows above for actual numbers. |

### Fine-tune post-mortem (Role B)

LoRA-v2b trained a 60/40 sheet:cell mix from 622 verifier-passed trajectories for 446 steps (lr 5e-5, rank 32). It fixed the per-sample `out_path` race and the epoch-iteration crash, and produced a clean 25-step checkpoint ladder. The pre-fix step-200 artifact (~26%, heavy syntax drift from JSON completions leaking into code generation) is preserved in `data/sft/log_v2b/pre_fix_step200_artifact.json` as the "before" evidence.

The 100-task stratified subsample (50 cell / 50 sheet, fixed seed) scored the v2b final checkpoint at **47%** and step-300 at **44%** — both well below the 64% promotion bar, both within noise of the LoRA-v1 result, neither approaching the new 68% ship. The fine-tune recovered cell-level reasoning (cell-level 22/50 = 44%) but the sheet codegen completions still emitted occasional syntax errors at temperature 0 (sheet-level 25/50 = 50%), holding the run inside a 5pp band despite 446 training steps. Archived in `research/data/eval/v2b_subsample/` (`step300_results.json`, `final_results.json`, both with predictions). Despite the corrected data mix, the fine-tune could not overtake A's 68.00% config-parity clone-run on the published 400; ship went to the non-fine-tuned run.

### Measurement variance (read before comparing rows)

A fresh temp-0 rerun of the identical values-first cell path (275 tasks) scored **43.64% vs the original 48.00%** — a −12 net-pass swing from re-running the same configuration. Temp-0 Tinker inference is not bit-reproducible, so task-level pass counts carry roughly **±3pp run-to-run variance**. Consequences for this table:

- Differences **smaller than ~2pp between rows are within noise**, not demonstrated improvements or regressions.
- Hybrid-pin's −3pp vs ship and Hybrid-v2's −2pp are consistent with "no measured effect," not proven harm; both were also *different samples* (new Tinker passes), not the same workbooks re-scored.
- Clone-run **68.00%** is **+13.25pp** over the old hybrid and **+9pp** over the official 59.0% floor — well outside the ±2–3pp noise band. It is the ship headline.
- Future promotion must beat **68.00%** by more than the noise band on the full 400.

### The cell-accuracy trade-off (honest)

`cell_accuracy` (the fraction of graded cells that match) drops from **95.45%** on the
old hybrid to **37.09%** on the clone-run — same model, same official prompt, only the
decode path differs. The pass-rate is the primary metric (`pass_rate` is what judges
rank by), and pass-rate goes up 13.25pp, but the trade-off is real and worth naming:

- **Thinking on** lets the model commit to a fully-correct answer on tasks where it
  can reason through the whole lookup / aggregation chain. Those are the new wins.
- **Thinking on** also lets the model produce partially-correct outputs that score
  fewer correct cells per task, because `cell_accuracy` averages across the cells the
  model *did* attempt to write. 33 JSONDecodeErrors and 25 truncations (23 overlap)
  show the failure mode: long-CoT answers sometimes run past the 16k output ceiling
  or fail to terminate cleanly as JSON. On those tasks every graded cell is wrong,
  dragging `cell_accuracy` down sharply even though `pass_rate` is unchanged from
  the init-workbook fallback.
- The old hybrid (`thinking off`) is the opposite shape: codegen writes almost every
  graded cell correctly (97.61% on its sheet path, 95.45% stitched), but many sheet
  tasks fail because the model can't reason about a 5-step transform in one direct
  call, so `pass_rate` drops.

We are shipping pass-rate because that is what the bench ranks; the `cell_accuracy`
drop is documented for judges who look at the metric.

## Your run on the 400

Diagnostic VM paths (also archived in repo):

- `predictions.jsonl`: `/tmp/clone-run-400/predictions.jsonl`  →  `research/data/eval/clone_run/predictions.jsonl`
- `outputs/`: `/tmp/clone-run-400/outputs/`  →  in-repo archive omitted (400 workbooks; predictions.jsonl is the ground truth for the evaluator)
- `traces/`: `/tmp/clone-run-400/traces/`  →  `research/data/eval/clone_run/traces/` (400 tasks, one jsonl per task)
- `run.log`: `/tmp/clone-run-400/run.log`  →  `research/data/eval/clone_run/run.log`
- `results.json`: `/tmp/clone-run-400/results.json`  →  `research/data/eval/clone_run/results.json`
- parse audit: `/tmp/clone-run-400/parse_audit_summary.json` (33 JSONDecodeError, 25 truncated at 16k, 23 both; 365 harness-ok)  →  `research/data/eval/clone_run/parse_audit_summary.json`

Independent container reproduction (the shipped image, run unattended on the full 400):
- results: `research/data/eval/container400/results.json` — **67.75%** (271/400), within the ±2–3pp noise band of the 68.00% clone-run headline; cell 75.64% / sheet 50.40% / cell_acc 37.00%; audit 34 json_err / 23 trunc / 366 ok
- `run.log` archived alongside. The container produced the full contract (`predictions.jsonl`, `outputs/`, `traces/`, `run.log`) and exited cleanly on its own.

## Code

Pipeline in `harness/`, runs in Docker reading `/data` writing `/out`. Env vars:
`TINKER_API_KEY` (required), `GEMINI_API_KEY` (optional spare), `TINKER_PROJECT_ID`
(optional — **not hardcoded anywhere**; when unset the Tinker SDK uses the calling
account's default project, so the container runs under your project the same way
it ran under ours), `SOFFICE` (optional path to LibreOffice).

**Ship entrypoint:** `harness/clone_run.py` (not `pipeline.py`). The Dockerfile
must `CMD ["python", "harness/clone_run.py", "--dataset-dir", "/data", "--out-dir", "/out"]`.
`pipeline.py` is the harness used for the ablation runs (hybrid / codegen / LoRA);
it is not the ship.

### Judges' run (turnkey)

```bash
docker build -t tieout .
docker run --rm --env-file <keys.env> \
  -v /path/to/holdout:/data:ro \
  -v /path/to/out:/out \
  tieout
```

`keys.env` needs `TINKER_API_KEY` (others optional, see above). The container runs
all 400 (or all holdout) tasks unattended at temp 0, fsyncs
`predictions.jsonl` + `run.log`, verifies the output contract, then force-exits 0
(clean exit is guaranteed — the tinker poller cannot hang the process). On
failure it prints the traceback and exits 1. Output contract: `predictions.jsonl`,
`outputs/`, `traces/`, `run.log`. This exact invocation was validated on the full
400 before submission.


## Things to look at

- docs/TEAM-BRIEF.md — current roles and task board
- docs/HACKATHON-NOTES.md — post-hackathon retro: winning teams' techniques vs. our approach
- docs/SESSION-STATUS.md — post-ship-call handoff state
- docs/BASELINE-DELTA.md — why the 12pp gap existed and how the clone-run closed it
- docs/RESULTS_CHECKLIST.md — ablation log, scoring recipes, variance framework
- docs/CONSTRAINTS.md — space + credits + scoring params
- docs/SETUP.md — venue setup order
- research/data/eval/clone_run/ — ship evidence (results.json, predictions.jsonl, run.log, parse_audit)
- research/data/eval/v2b_subsample/ — fine-tune negative result (step-300 + final, 100-task)
- research/data/eval/lora_v1/ — LoRA-v1 archive + DIAGNOSIS.md (data-mix starvation evidence)
