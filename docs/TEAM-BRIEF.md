# Team brief — three-way split (2026-09-05)

Adib's ruling: **use any approach you like** — Qwen-only constraint lifted. Deterministic
tooling (LibreOffice recalc), teacher models, and any inference capacity are in play.
Everything still ships inside the container contract: `/data` read-only → `/out` with
`predictions.jsonl`, `outputs/`, `traces/`, `run.log`. Missing line or file = 0.

Shared context: `research/methodology-notes.md` (source of truth), `docs/SESSION-STATUS.md`
(state), `docs/CONSTRAINTS.md` (scoring: pass_rate primary, cell_accuracy tie-break,
held-out private fund dataset, write-up judged with results).

Resources in play:
- Tinker account #1 (`.env` `TINKER_API_KEY`) — primary sampling + fine-tune.
- Tinker account #2 (separate Thinking Machines account) — parallel sampling at scale
  for data generation, or a second fine-tune experiment.
- Modal — cheap massive-parallel sampling (best-of-n, rejection sampling) and headless
  LibreOffice recalc if the Mac/VM can't take it.
- Fastino / Pioneer (`.env` keys) — extra capacity; teacher/analysis only, nothing from
  them ships in the graded pipeline without a note in SUBMISSION.md.

The single biggest documented lever is **execution feedback in the loop** (~2.5x in the
SpreadsheetBench ablation; the core of WML's 74.67 on this exact track). Work to that.

---

## A — Harness: execution feedback + codegen loop

Owns: `harness/pipeline.py`, `harness/executor.py`, `harness/prompts.py`, `harness/verifier.py`.

1. Wire the dormant `CODEGEN_SYSTEM` path into the pipeline: sheet-level tasks (and
   cell-level tasks that fail N times values-first) go
   serialize → write openpyxl code → execute in-sandbox (timeout, capture stderr) →
   read back written cells → attribution-guided repair on the *executed* result.
2. Model-written code runs inside the container only, per container contract. No host
   paths, no network in the exec sandbox.
3. Add deterministic post-check: if `soffice` available (`SOFFICE` env), recalc-convert
   output and verify graded cells have non-error values before shipping; fall back
   silently when absent (Mac has no LibreOffice by rule).
4. Keep the values-first path as the always-works fallback (never blank, best guess
   after MAX_ATTEMPTS). Do not regress the committed repair loop (93d109c).
5. Acceptance: smoke IDs `13-1`, `51-12` pass both paths; a 20-task sheet-level subset
   improves vs the no-repair baseline in `/tmp/tinker-400`.

## B — Training: expert iteration (STaR) on Tinker

Owns: data generation, SFT set construction, fine-tune runs, eval of checkpoints.

1. Rejection sampling: run the harness (values + codegen paths) with temp ~0.7, n≈8 per
   task, at scale — Modal or Tinker account #2; keep trajectories whose output passes
   the verifier / sanity gate. Target ≥200 verified trajectories before first run.
2. Build SFT set: prompt → clean JSON answer (strip thinking, keep format the parser
   likes). Dedupe; balance cell-level (275) vs sheet-level (125) mix.
3. LoRA fine-tune Qwen3.8-27B via Tinker (`peft`), eval temp 0 on the same 400 with
   fixed ordering; compare vs 59.0% base and vs no-repair baseline. Report mean±std on
   a repeatable subset (WML protocol: seed-42, 3 seeds).
4. Iterate: failures of checkpoint v1 feed v2 data (expert iteration), not guesswork.
5. Track tokens/cost; the checkpoint is also the latency hedge (one-shot vs 3-turn repair).

## C — Measurement: scoring, taxonomy, skills, write-up

Owns: evaluation runs, failure taxonomy, skill/prompt-fragment library, SUBMISSION.md.

1. When `/tmp/tinker-400` finishes: score it
   (`uv run evaluate.py --predictions ... [--no-recalc]`), record in RESULTS_CHECKLIST.
   This is the no-repair baseline number.
2. Build failure taxonomy from `/tmp/tinker-400/traces`: per instruction_type, classify
   truncation vs reasoning vs serialization vs parse; quantify retry recovery. This
   drives A's priorities and B's data mix — publish numbers, not anecdotes.
3. Skill library (notes §4.4): reusable prompt-fragments per *task category* (lookup
   rebuild, aggregation/pivot, date arithmetic, sheet reorg…), retrieved by category at
   prompt time. Generic patterns only — the held-out private fund set punishes overfit.
4. Own the write-up skeleton + SUBMISSION.md as results land; log every run
   (model, n, temp, out-dir) so the ablation table writes itself.
5. Housekeeping: fixed task ordering/seeds everywhere; never commit keys.

---

## Sequencing

- Now: C's taxonomy (waits on `/tmp/tinker-400`) and A's codegen loop (independent) start
  in parallel; B sets up Modal/account-2 sampling immediately.
- First checkpoint eval once ≥200 trajectories exist (B), scored by C with the same rig.
- Ship decision T-3h: best measured combo on all 400 (`--all`), values-first fallback
  always present.
