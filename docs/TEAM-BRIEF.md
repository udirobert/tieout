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
| task_0011 | A | **done** | Write-path: numerics as numbers, strip string cells (`normalize_cell_value`). 61-4 class; 341-40 type-match. |
| task_0012 | A | **done** | Wire `harness/skills.py` `get_skill_fragment` into codegen **system** prompt (lookup / agg / sheet-reorg / date). |
| task_0013 | A | **in_progress** | Full 400 codegen headline → `/tmp/tinker-400-codegen`. Gate: re-run 20 sheet ids first. Conc 4; B stays on acct #2 / Modal. |

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
