# Team brief — three-way split (2026-09-05)

> **Superseded for Syndicate.** Active plan: `SYNDICATE.md`, `docs/SYNDICATE-DEMO.md`,
> `docs/SESSION-STATUS.md`. This file preserves the Encode weekend task board.

Adib's ruling: **use any approach you like** — Qwen-only constraint lifted. Deterministic
tooling (LibreOffice recalc), teacher models, and any inference capacity are in play.
Everything still ships inside the container contract: `/data` read-only → `/out` with
`predictions.jsonl`, `outputs/`, `traces/`, `run.log`. Missing line or file = 0.

Shared context: `research/methodology-notes.md` (methodology), `docs/SESSION-STATUS.md`
(state), `docs/CONSTRAINTS.md` (scoring: pass_rate primary, cell_accuracy tie-break,
## PRIORITY RE-BASELINE (2026-09-05 evening — read first)

Full hackathon brief read. Research track confirmed. Four facts change priorities:

1. **Official Qwen3.8-27B baseline is 59.0% one-shot. Our ship is 54.75% — we are
   4.25pp BELOW the floor.** Our internal 46.75% baseline is 12pp below official.
   The gap is harness config (prompt / FORMAT_HINT / max_tokens / parsing / repair),
   not model. Closing it generalizes to the holdout by construction and is the
   highest-expected-pp action remaining. **This is now priority 1 for A.**
2. **Judges run the container on a HOLDOUT set we have never seen.** Id-keyed
   artifacts (the `#N/A` whitelist ids, known-too-large skip list, per-id notes)
   contribute ZERO on holdout. Everything shipped must be generic: general policies,
   general repair, general prompts. Reposition the whitelist in docs as a general
   missing-lookup policy with example ids, not an id list.
3. **Code review is part of judging** ("you can defend it"). The variance framework,
   negative-result rows, and decision rules are judging assets. Keep them current.
4. **Clock:** submissions close **Sun 12:00**; demo video recorded **Sun 11:00**;
   judges run the container **unattended, first time, read-only /data**.

### Re-prioritized plan (remaining ~30h)

- **P1 — A: baseline reconciliation.** Diff our values-first config against the
  official 59.0% one-shot config. Every pp recovered lifts the whole ladder,
  holdout included. One cycle, report deltas before touching anything.
- **P1 — Orchestrator: container dry-run.** Full unattended container run
  (fresh clone, read-only /data mount, env vars only) before Sun 09:00. First-time-
  it-works is a pass/fail criterion we have not yet tested.
- **P2 — B/C: v2 checkpoint eval.** Already running; costs nothing extra. Promotion
  bar: ≥56.75% on full 400 (≥64.0% on the 100-subsample). A genuine fine-tune win
  over the official-style baseline is the demo headline.
- **P3 — freeze ablation exploration.** No more pin/overlay variations: sub-noise.
- **P3 — demo video owner assigned; recorded Sun 09:00–11:00.**
- **P4 — write-up freeze Sun 10:00**: SUBMISSION.md must be final except for the
  last eval numbers.

---

held-out private fund dataset, write-up judged with results). `docs/PLAN.md` and
`docs/PATTERNS.md` are superseded — do not follow them.

## Orchestrator

Fourth member / tech lead. Coordinates A/B/C: spawn each role with this brief,
review diffs, sequence the board, make the ship call. Has done smoke, launched
the `/tmp/tinker-400` baseline, landed the first repair loop. Keeps final
integration; A owns the codegen loop day-to-day.

## Owners

- **A — Harness** — Cursor agent. Exclusive owner of `harness/*.py`.
- **B — Training** — TBD. Data-gen scripts + Tinker training. No `harness/*.py`.
- **C — Measurement** — TBD. `evaluate.py`, traces, `skills/library.py`, SUBMISSION.md.

## Resources

- Tinker account #1 (`.env` `TINKER_API_KEY`) — `ts400` **has finished**. Still:
  B should prefer Modal / acct #2 so A smoke and B sampling do not collide.
- Tinker account #2 — B rejection sampling / second experiment.
- Modal — B scale + headless LibreOffice if needed.
- Fastino / Pioneer — teacher/analysis only; nothing from them in the graded
  pipeline without a SUBMISSION.md note.
- Gemini (`GEMINI_API_KEY`) — A's spare for smoke so we do not collide with `ts400`.

The single biggest documented lever is **execution feedback in the loop** (~2.5x in the
SpreadsheetBench ablation; the core of WML's 74.67 on this exact track). Work to that.

---

## Task board

Update status in place. A owns 0001 / 0007 / 0008 / 0009. Do not edit `harness/*.py`
except A.

| id | owner | status | task |
|---|---|---|---|
| task_0001 | A | **done** | Wire codegen/execution-feedback loop into `pipeline.py` (exclusive `harness/*.py`) |
| task_0002 | B | **done** | 226 verified SFT trajectories (gate ≥200). Quality-gate clean. Sampler keeps running for expert-iteration v2. |
| task_0003 | B | **done** | LoRA-v1 scored **32.25%** / cell 46.6 / sheet 0.8. Not ship. Cause: data-mix starvation of codegen completions; overtrained on 202 records. |
| task_0004 | C | **done*** | `/tmp/tinker-400` finished (400/400). `results.json` summary: **pass_rate 0.4675**, cell_accuracy 0.3728, cell 0.48 / sheet 0.44. Harness log: 373 ok / 14 partial / 13 error. *C should still paste into RESULTS_CHECKLIST / SUBMISSION and confirm whether scoring used recalc.* |
| task_0005 | C | **unblocked** | Failure taxonomy from `/tmp/tinker-400/traces`. A already sees: missing large ranges, JSONDecodeError on 30k+ replies, MergedCell writes, sheet-level prose. |
| task_0006 | C | in_progress | Skill library (`skills/library.py` `fragment_for`) + write-up skeleton. A already calls the hook. |
| task_0007 | A | **done** | Gemini smoke on VM: `--path values` and `--path codegen` both **PASS** official `--no-recalc` on `13-1` (120/120) and `51-12` (1/1). `13-1` failed the tinker-400 baseline. |
| task_0008 | A | **done** | 20 tinker-400 sheet-fails, Tinker Qwen `--path auto` on VM. **11/20 PASS (0.55)**, cell_accuracy **0.9911** vs **0.00** pass on the same ids in `/tmp/tinker-400`. Log `/tmp/sheet20-codegen`. Near-misses: 341-40 (2dp), 61-4 (trailing space). 13-1 failed on Qwen (31/120) after passing Gemini smoke. |
| task_0009 | A | **done** | `--path {auto,values,codegen}` + `--temperature` so A can force paths and B can sample at 0.7 without touching harness files. |
| task_0010 | A | **done** | Write through merged cells (`MergedCell` was a hard error on 208-20 / 38703 / 55060). |
| task_0011 | A | **done** | Write-path: numeric strings → int/float. Do **not** strip text (goldens keep padding; strip broke 80-42 / 290-27 on the gate). |
| task_0012 | A | **done** | Wire `harness/skills.py` `get_skill_fragment` into codegen **system** prompt (lookup / agg / sheet-reorg / date). |
| task_0013 | A | **done** | `/tmp/tinker-400-codegen` scored (`--all --no-recalc`): **pass_rate 0.5175**, cell_acc **0.9761**, cell **0.4364**, sheet **0.696**. Vs tinker-400 0.4675 / 0.3728 / 0.48 / 0.44. Sheet +25.6pp; cell −4.4pp. **Tinker quota free — B may resume.** |
| task_0014 | A | **done** | Hybrid stitch (cell←values `/tmp/tinker-400`, sheet←codegen `/tmp/tinker-400-codegen`): **pass_rate 0.5475**, cell **0.48**, sheet **0.696**, cell_acc **0.9545**. Ship default `--path hybrid` (no cross-path fallback). A on standby for C's recalc-gate. |
| task_0015 | A | **done** | C pin-leak fix: `_answer_range_excerpt` emits addresses only (no init values). Recalc-as-gate: soffice `#ERR!` on sheet codegen → discard workbook → values-first. No new Tinker run. |
| task_0016 | A | **done** | Pin-fix 27-cell re-score (`--path hybrid --temperature 0`, n=1, 66.3s). Overlay 19/27 held, **8 regressions**. hybrid-v2 `--all --no-recalc`: **52.75%** / cell **45.09%** / sheet **69.6%**. Ship stays `/tmp/tinker-400-hybrid` **54.75%**. Pin-omit on values-first is not free. |
| task_0017 | A | **done** | Recalc-gate proven on VM LibreOffice 24.2.7: `#DIV/0!` `#REF!` `#NAME?` fail; clean `SUM`/literal pass; 4 real sheet tasks (13-1, 17-35, 22-47, 23-24) fire; hybrid fake-completer codegen→values fallback writes 7 not `=1/0`. Script: `research/prove_recalc_gate.py`. |
| task_0018 | A | **done** | Pin-scope landed (codegen omits init values; values-first keeps them). 275-cell `--path values` temp 0 + codegen sheets: **51.75%** / cell **43.64%** / sheet **69.6%**. +14/−26 vs old hybrid cells. Does not clear 54.75%. Ship stays `/tmp/tinker-400-hybrid`. |
| task_0019 | A | **done** | Written delta: `docs/BASELINE-DELTA.md`. Thinking off vs official `qwen3_5` renderer is the 8–12pp story; 20k cap +1–2pp. FORMAT_HINT/repair/scoring/max_tokens are not the 12pp gap. No `pipeline.py` change. Holdout: no new id-keys; `#N/A` must be a general scalar policy, not an id whitelist. |
| task_0024 | A | **done** | Clone-run `/tmp/clone-run-400` `--all --no-recalc`: **68.00%** (272/400), cell **73.82%**, sheet **55.20%**, cell_acc 37.09%. Audit: 33 JSONDecodeError / 25 trunc / 365 harness-ok. **PROMOTE — new ship.** Container must run `harness/clone_run.py`, not hybrid `pipeline.py`. Tinker quota free for container-400. |
| task_0020 | Orchestrator | **done** | Container-400 completed unattended: 400/400 graded, clean exit, full contract. Official scorer: **67.75%** (271/400) — reproduces ship 68.00% within noise (−0.25pp). Audit: 34 json_err / 23 trunc / 366 ok (clone-run: 33/25/365). Artifacts archived at `research/data/eval/container400/`. |
| task_0021 | Orchestrator | **pending** | Demo video: recorded Sun 09:00–11:00, uploaded before 12:00 close. Owner: orchestrator; script from SUBMISSION.md ablation + variance framework. Core story: same model, two configs, −13.25pp harness gap; thinking-on beats official floor by +9pp. |
| task_0022 | C | **done** | De-id-keying complete (C close-out 2026-09-05): `#N/A` is a general missing-lookup policy in SUBMISSION.md; variance framework and negative rows (LoRA-v1, hybrid-pin, v2b subsamples) frozen judge-facing. No ids leaked. |
| task_0023 | B/C | **done** | v2b trained 446/446; insurance subsample evals done (step-300: 44%, final: 47% — both below bar, closed as negative-result rows with archived artifacts in `research/data/eval/v2b_subsample/`). Post-mortem in SUBMISSION.md. |

`ts400` loaded old code at start — it is the no-repair baseline. Nobody else edits
`pipeline.py`. When A edits it, A owns it exclusively.

---

## A — Harness: execution feedback + codegen loop

Owns: `harness/pipeline.py`, `harness/executor.py`, `harness/prompts.py`, `harness/verifier.py`.

1. ~~Wire `CODEGEN_SYSTEM` into the pipeline~~ LANDED (task_0001).
2. ~~Sandbox~~ LANDED: temp-dir copy of init (goldens not visible), import allowlist, 120s, keys stripped.
3. ~~soffice post-check~~ LANDED: silent skip on this Mac.
4. Values-first fallback kept. Default `--model tinker:Qwen/Qwen3.8-27B`.
   `--resume` / `--fresh`. `--path` / `--temperature` (task_0009).
5. Acceptance: task_0007 (smoke both paths) then task_0008 (20-task sheet subset).

CLI for B (do not edit harness):

```
python harness/pipeline.py --dataset-dir /data --out-dir /tmp/star-n \
  --temperature 0.7 --concurrency 8 --model tinker:Qwen/Qwen3.8-27B
```

CLI for A smoke (Gemini, both paths):

```
python harness/pipeline.py --dataset-dir <data> --out-dir /tmp/smoke-values \
  --ids 13-1,51-12 --path values --model gemini:gemini-3.7-flash --fresh
python harness/pipeline.py --dataset-dir <data> --out-dir /tmp/smoke-codegen \
  --ids 13-1,51-12 --path codegen --model gemini:gemini-3.7-flash --fresh
```

## B — Training: expert iteration (STaR) on Tinker

Owns: data generation, SFT set construction, fine-tune runs, eval of checkpoints.
Start on Modal / account #2 immediately — do not share Tinker #1 with `ts400`.

1. Rejection sampling: harness with `--temperature 0.7`, n≈8 per task; keep
   trajectories that pass the verifier / sanity gate. Target ≥200.
2. SFT set: prompt → clean JSON (strip thinking). Dedupe; 275/125 mix.
3. LoRA Qwen3.8-27B via Tinker (`peft`), eval temp 0, fixed ordering.
4. v2 data from checkpoint failures (expert iteration).
5. Track tokens/cost.

## C — Measurement: scoring, taxonomy, skills, write-up

Owns: evaluation runs, failure taxonomy, `skills/library.py`, SUBMISSION.md.

1. Score `/tmp/tinker-400` when it finishes (`evaluate.py --predictions ...`).
2. Taxonomy from traces: truncation vs reasoning vs serialization vs parse;
   quantify retry recovery. Messages to A, not code edits in `harness/`.
3. Skill fragments in `skills/library.py` (`fragment_for(task) -> str`). Generic
   only. A already injects a non-empty return into values + codegen prompts.
4. Write-up + run log (model, n, temp, out-dir).
5. Fixed ordering/seeds; never commit keys.

---

## Sequencing

- Now: A smokes on Gemini (0007). B starts Modal/acct-2 sampling (0002). C builds
  eval rig + skills stub + write-up (0004/0006). Taxonomy waits on `ts400`.
- 0008 (sheet subset) after 0004. First checkpoint after ≥200 trajectories (0003).
- Ship decision T-3h: best measured combo on all 400 (`--all`). Dockerfile still
  orchestrator-owned, not this pass.

---

## Blockers & concrete resolutions (2026-09-05, ~16:15)

**Blocker 1 — Tinker org quota contention (B throttled to ~2 trajectories/check).**
A's full-400 codegen run on the VM and B's sampler are fighting over one org quota.
RESOLUTION (sequenced, not shared):
1. A's VM run has priority — it finishes first; nobody else samples until it does.
2. B PAUSES the sampler now (safe: trajectories.jsonl is append-only; the 51 banked
   records are verified). B uses the pause to land the format fix (Blocker 2).
3. When C posts A's scored result, B resumes at FULL concurrency on the free account.
   Sequential full-speed beats two throttled runs — both land sooner.
4. Account #2 / Modal are reserved for task_0003's eval fan-out, NOT for competing
   with A's run. If schedule forces parallelism later, the mover throttles to half
   concurrency — never both at full.

**Blocker 2 — `completion`-field contamination in trajectories.jsonl (records avg
213k chars, max 6.7M — workbook/prompt echo, not the answer).**
RESOLUTION (repair in place; no re-sampling — replies are clean: 0 think leaks,
51/51 parse):
1. B scripts a one-pass repair: rewrite each record's `completion` to the canonical
   parsed form `{"cells": [{"cell": "...", "value": ...}]}` from parser output.
2. Add a write-time assert (`len(completion) < 8000`) in sample_data.py so
   contamination cannot silently recur.
3. Commit the repaired dataset + fixed sampler before the count passes ~200 —
   repairing 51 is minutes; repairing 200+ risks mistakes.
4. task_0002 sign-off gate is now: >=200 verified trajectories AND clean completions
   (C runs the quality script before sign-off).

**Blocker 3 — task_0003 (fine-tune) start.**
RESOLUTION: launches the moment task_0002's gate passes. Data = canonical parsed
completions only; prompt format = post-55781f2 harness (skills-in-prompt, numeric
writes). The ~51 pre-fix records are repaired (Blocker 2), not discarded. Eval on
all 400, temp 0, fixed ordering, vs the 46.75% values baseline and A's codegen
number. Checkpoint = ship candidate AND latency hedge.

**Standing rule**: exactly one heavy Tinker consumer at a time; the other role waits
or uses account #2/Modal for eval-only work. Post quota intent ("launching, until
~HH:MM") to the mission log before any big run.

### Decisions made — final, do not re-litigate (2026-09-05, ~17:00)

- **B does NOT move to Modal for task_0002.** That was the fix for quota contention
  while A and B shared one Tinker org; A's VM run has finished and B already
  relocated sampling to the VM at full speed (105+/200 and climbing). B stays on
  the Tinker VM. Modal / account #2 are reserved exclusively for task_0003's eval
  fan-out (parallel temp-0 sweep across all 400).
- **Single blocking item for task_0002**: the `completion`-field fix. Sequence:
  commit write-time fix (canonical `{"cells":[...]}` + `<8k` chars assert) →
  pause sampler → repair existing records to `trajectories.jsonl.repaired` →
  verify quality gate → swap → resume. Land it before the count crosses 200.
- **Gate for task_0002 sign-off**: ≥200 verified trajectories AND clean completions
  (mean length ~1–3k chars, 0 think leaks, 0 parse failures), confirmed by C's
  quality script. task_0003 fires immediately after.
- Standing rule satisfied today: one heavy consumer (B) only.
