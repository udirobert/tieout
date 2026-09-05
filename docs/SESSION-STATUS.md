# Session status / handoff (updated 2026-09-05, post-smoke + full-run launch)

Fresh-context handoff. Read `research/methodology-notes.md` first — it is the source of
truth for methodology decisions. Then this file for state.

## Goal
Beat 59.0% baseline on SpreadsheetBench Verified 400 with Qwen3.8-27B via Tinker, guided
by published methodology (no trial-and-error).

## State
- **adapters.py** (`harness/adapters.py`): `enable_thinking=False` on the model's own HF
  chat template (confirmed correct vs Tinker's `qwen3_5_disable_thinking` renderer —
  same empty-`<think></think>` prompt), `max_tokens=16384`, temp 0. Committed.
- **SMOKE PASSED (2026-09-05)**: `13-1`, `51-12` via Tinker Qwen3.8-27B — no `<think>`
  leak, replies end at `<|im_end|>` (no truncation), clean JSON, both `ok` in 1 attempt.
  Traces in `/tmp/tinker-smoke`.
- **FULL 400-TASK RUN RUNNING**: screen `ts400`, log `/tmp/tinker-400.log`,
  out `/tmp/tinker-400` (Qwen3.8-27B, concurrency 8, ~55s/task wall).
  Next: score with `uv run evaluate.py --predictions /tmp/tinker-400/predictions.jsonl`
  (VM if recalc needed; `--no-recalc` locally for values-first v0).
- **Attribution-guided repair LANDED (harness/pipeline.py + prompts.py)**: attempt 1 uses
  `build_values_prompt`; on sanity/parse/write failure, attempts 2–3 send
  `build_repair_prompt` (rejected reply + failure reason + graded cells, smallest-edit
  instruction). Blind identical-prompt resample is gone. Validated by fake-completer
  failure-injection (bad answer → repair prompt → ok, 2 attempts). Committed.
- **research/search.py**: Parallel Search API helper (`PARALLEL_API_KEY` in gitignored
  `.env`; key redacted never commit). Uses curl (python.org 3.14 lacks SSL certs).
  `python3 research/search.py --objective "..." -q "..."` → excerpts for the notes.
- **methodology-notes.md §6** has the 2026-09-05 Parallel search sweep: verified SOTA on
  our track is 59.25% (Shortcut); paper ablation shows execution feedback ≈2.5x;
  Tinker Qwen3.8-27B = Hybrid+Vision 64K, current (not retired).

## Next steps (in order)
1. ~~Rerun Tinker smoke~~ DONE 2026-09-05 — clean (see State).
2. ~~Full 400-task research-track run~~ RUNNING — screen `ts400`, `/tmp/tinker-400.log`;
   when done: `uv run evaluate.py --predictions /tmp/tinker-400/predictions.jsonl`.
   Note: this run predates the repair loop (it loaded the old code at start) — it is the
   no-repair baseline; a second full run with repair can follow if it beats 59.0% or if
   retries are material in traces.
3. ~~Attribution-guided repair in pipeline.py~~ DONE + committed (93d109c).
4. ~~Ask Adib~~ ANSWERED: "use any approach you like" — Qwen-only lifted; LibreOffice
   recalc + teacher models + extra capacity all legal. Team split: `docs/TEAM-BRIEF.md`
   (A harness/codegen, B expert-iteration training, C measurement/skills/write-up).
5. Later: per-category skill/prompt-fragment library (retrieval-instructed beats direct).

## Process rules
- Before any harness change: check methodology-notes.md + source papers.
- Model calls only to *measure* against published hypotheses.
- Venue-first constraints still apply (`docs/CONSTRAINTS.md`): no dataset download,
  no LibreOffice, no docker build on this Mac.
