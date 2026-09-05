# Team brief — three-way split (2026-09-05)

Adib's ruling: **use any approach you like** — Qwen-only constraint lifted. Deterministic
tooling (LibreOffice recalc), teacher models, and any inference capacity are in play.
Everything still ships inside the container contract: `/data` read-only → `/out` with
`predictions.jsonl`, `outputs/`, `traces/`, `run.log`. Missing line or file = 0.

Shared context: `research/methodology-notes.md` (methodology), `docs/SESSION-STATUS.md`
(state), `docs/CONSTRAINTS.md` (scoring: pass_rate primary, cell_accuracy tie-break,
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
| task_0002 | B | in_progress | Rejection-sampling data gen at scale (Modal / Tinker acct #2). Use `--temperature 0.7`. Current committed harness already emits trajectories; v2 improves now that codegen has landed. |
| task_0003 | B | blocked on 0002 | First LoRA fine-tune + checkpoint eval → after ≥200 verified trajectories |
| task_0004 | C | **done*** | `/tmp/tinker-400` finished (400/400). `results.json` summary: **pass_rate 0.4675**, cell_accuracy 0.3728, cell 0.48 / sheet 0.44. Harness log: 373 ok / 14 partial / 13 error. *C should still paste into RESULTS_CHECKLIST / SUBMISSION and confirm whether scoring used recalc.* |
| task_0005 | C | **unblocked** | Failure taxonomy from `/tmp/tinker-400/traces`. A already sees: missing large ranges, JSONDecodeError on 30k+ replies, MergedCell writes, sheet-level prose. |
| task_0006 | C | in_progress | Skill library (`skills/library.py` `fragment_for`) + write-up skeleton. A already calls the hook. |
| task_0007 | A | **done** | Gemini smoke on VM: `--path values` and `--path codegen` both **PASS** official `--no-recalc` on `13-1` (120/120) and `51-12` (1/1). `13-1` failed the tinker-400 baseline. |
| task_0008 | A | **done** | 20 tinker-400 sheet-fails, Tinker Qwen `--path auto` on VM. **11/20 PASS (0.55)**, cell_accuracy **0.9911** vs **0.00** pass on the same ids in `/tmp/tinker-400`. Log `/tmp/sheet20-codegen`. Near-misses: 341-40 (2dp), 61-4 (trailing space). 13-1 failed on Qwen (31/120) after passing Gemini smoke. |
| task_0009 | A | **done** | `--path {auto,values,codegen}` + `--temperature` so A can force paths and B can sample at 0.7 without touching harness files. |
| task_0010 | A | **done** | Write through merged cells (`MergedCell` was a hard error on 208-20 / 38703 / 55060). |
| task_0011 | A | **done** | Write-path: numeric strings → int/float. Do **not** strip text (goldens keep padding; strip broke 80-42 / 290-27 on the gate). |
| task_0012 | A | **done** | Wire `harness/skills.py` `get_skill_fragment` into codegen **system** prompt (lookup / agg / sheet-reorg / date). |
| task_0013 | A | **in_progress** | Full 400 → `/tmp/tinker-400-codegen` (**327/400** at 16:29, conc 4, ETA ~16:50). A has the org quota; B paused until C posts this score. |

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
