# Session status / handoff (updated 2026-09-06, container validated)

Read `docs/TEAM-BRIEF.md` then this file.

## ✅ Container validated (2026-09-06, pre-09:00)
- Image built from pushed repo (10.4GB; torch+CUDA wheels dominate). Entrypoint is `harness/clone_run.py` with the fsync + `os._exit(0)` clean-exit fix; failure path exits 1 with traceback.
- **Smoke (2 tasks) passed three times over**, final run on the pushed repo: both tasks `ok`, full contract written (`predictions.jsonl`, `outputs/`, `traces/`, `run.log`), container exits cleanly (`--rm` reaped it). The tinker-poller hang found in the first dry-run is fixed.
- **Full-400 unattended container run is live** (`/tmp/container400`, concurrency 4, temp 0). ETA ~3.5h — lands before the 12:00 freeze. Score check on completion: expect ~68% (±noise).
- Judges' turnkey `docker run` invocation documented in SUBMISSION.md ("Judges' run" section).
- Gotcha for anyone rebuilding: `.dockerignore` must NOT exclude `research/baseline/` (`clone_run.py` imports `common.py` from there — the build fails with "COPY failed" if excluded). Fixed and pushed.

## ⚠ Ship call: clone-run promoted (2026-09-05, ~22:30)
- **Clone-run promoted to ship headline**: 68.00% / 272/400, cell 73.82%, sheet 55.20%, cell_acc 37.09%.
- Old hybrid 54.75% superseded; stays in the ablation table as the harness-gap finding (same model, thinking off, wrong decode path).
- Container entry must be `harness/clone_run.py`, NOT `pipeline.py` (which runs the old hybrid). Anyone rebuilding the image: replace the entrypoint and rebuild before the dry-run.
- **Cell-accuracy trade-off**: 37.09% on clone-run vs 95.45% on old hybrid — thinking-on gets more tasks fully right but produces partial / truncated outputs on a long tail (33 JSONDecodeError + 25 trunc, 23 overlap). Documented in SUBMISSION.md "The cell-accuracy trade-off".

## Strategic re-baseline (still relevant — read first)
- Official Qwen3.8-27B one-shot floor is **59.0%**. Clone-run ship is **+9pp over the floor, +21.25pp over the 46.75% internal baseline, +13.25pp over the old hybrid**. The harness gap is closed; the lift is decode-path, not prompt or parser.
- Judges score the container on a **holdout set**: id-keyed artifacts are worthless there; all shipped behavior must be generic. `task_0022` (de-id-keying) is **done** — `#N/A` is a general missing-lookup policy in SUBMISSION.md; no per-id whitelist.
- Container judged **unattended, first time, read-only /data** → dry-run is P1 (task_0020). Demo video Sun 09:00–11:00, submissions close Sun 12:00 (task_0021).
- Promotion bar vs ship: ≥70.00% full-400 / ≥66.0% on the 100-subsample (±2–3pp noise band documented in SUBMISSION.md + RESULTS_CHECKLIST.md).

## Headline (ship candidate)
`/tmp/clone-run-400` `--all --no-recalc`: **pass_rate 0.68** (272/400), cell **0.7382**,
sheet **0.552**, cell_acc 0.3709. `qwen3_5` thinking on, official prompt, our parse/write.
Old hybrid 54.75% is superseded (harness-gap: thinking off).
**Container entry must be `harness/clone_run.py` before the unattended 400.**

## Ablation (current as of ship call)
- values-first `/tmp/tinker-400`: 46.75% / cell 48% / sheet 44% (thinking off, internal baseline)
- codegen-auto `/tmp/tinker-400-codegen`: 51.75% / cell 43.64% / sheet 69.6%
- hybrid stitch `/tmp/tinker-400-hybrid`: 54.75% / cell 48% / sheet 69.6%  ← superseded
- hybrid-v2 pin-omit overlay: 52.75% / cell 45.09% / sheet 69.6%
- hybrid-pin (scoped, fresh cells): 51.75% / cell 43.64% / sheet 69.6%
- **clone-run `/tmp/clone-run-400`: 68.00% / cell 73.82% / sheet 55.20% / cell_acc 37.09%  ← SHIP**
- LoRA-v1: 32.25% / cell 46.55% / sheet 0.80% — data-mix starvation; overtrained on 202 records
- v2b subsample (step-300): 44% / cell 40% / sheet 48% — 100-task; below 64% promotion bar
- v2b subsample (final): 47% / cell 44% / sheet 50% — 100-task; below 64% promotion bar
- WML reference: 74.67%

## A status
task_0018 (pin-scope), task_0019 (BASELINE-DELTA.md), task_0024 (clone-run) all **done**. Container rebuild with `harness/clone_run.py` entrypoint is the next A deliverable.

## Measurement variance
Temp-0 rerun of identical values-first cells: 43.64% vs original 48.00% → ±3pp run-to-run noise. Sub-2pp ablation differences are within noise. The 13.25pp clone-run lift is **outside** the noise band (same model, same official prompt, only the decode path differs). Promotion to a new ship requires >noise-band win on the full 400 over **68.00%** (≥70.00%).

## B status
LoRA-v1: 32.25% (sheet 0.8%) — negative; cause: codegen starvation + overtraining on 202 records.
v2b: **done** (446 steps, lr 5e-5, 60/40 sheet:cell mix from 622 banked trajectories). The pre-fix step-200 crashed-run artifact (~26% syntax drift) and post-fix step-300 + final subsample evals (44% / 47%) are archived. Did not clear the 64% promotion bar on the 100-subsample; ship stayed with the non-fine-tuned clone-run. Documentation: `research/data/eval/v2b_subsample/`, `research/data/eval/lora_v1/`.

## C status
- LoRA-v1 artifacts frozen in `research/data/eval/lora_v1/` (+DIAGNOSIS.md: trailing syntax drift). Canonical 32.25% reconciled across SUBMISSION.md, RESULTS_CHECKLIST.md, lora_v1/DIAGNOSIS.md.
- Variance framework committed in SUBMISSION.md "Measurement variance" and RESULTS_CHECKLIST.md §E; promotion bar ≥70.00% / ≥66.0% subsample.
- Step-200 crashed-run subsample scored at 26% (matches v1 root cause); step-300 v2b at 44%; v2b final at 47%; clone-run independently re-scored at 68.00%. All archived locally (`research/data/eval/v2b_subsample/`, `research/data/eval/clone_run/`).
- Ship container dry-run verification — pending; queued behind container rebuild with `clone_run.py` entrypoint.

## Ship container
- **Entrypoint: `harness/clone_run.py`** (was: `pipeline.py` with `--path hybrid`).
- Config: `qwen3_5` renderer (thinking on), official SYSTEM_PROMPT + FORMAT_HINT, full 120×30 serialize (no 20k cap), `max_tokens=16384`, temperature 0, renderer stop sequences. Container env: `TINKER_API_KEY` (required), `TINKER_PROJECT_ID` (optional), `SOFFICE` (optional, for the recalc gate).
- Pin-scope, skills fragments, repair loop, codegen path — **not in the ship container**. They remain in `pipeline.py` for the ablation runs but the ship runs `clone_run.py`.
