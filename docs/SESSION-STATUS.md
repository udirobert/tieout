# Session status / handoff (updated 2026-09-05, pre-restart)

Fresh-context handoff. Read `research/methodology-notes.md` first — it is the source of
truth for methodology decisions. Then this file for state.

## Goal
Beat 59.0% baseline on SpreadsheetBench Verified 400 with Qwen3.8-27B via Tinker, guided
by published methodology (no trial-and-error).

## State
- **adapters.py** (`harness/adapters.py`): `enable_thinking=False` on the model's own HF
  chat template (confirmed correct vs Tinker's `qwen3_5_disable_thinking` renderer —
  same empty-`<think></think>` prompt), `max_tokens=16384`, temp 0. Committed.
- **research/search.py**: Parallel Search API helper (`PARALLEL_API_KEY` in gitignored
  `.env`; key redacted never commit). Uses curl (python.org 3.14 lacks SSL certs).
  `python3 research/search.py --objective "..." -q "..."` → excerpts for the notes.
- **methodology-notes.md §6** has the 2026-09-05 Parallel search sweep: verified SOTA on
  our track is 59.25% (Shortcut); paper ablation shows execution feedback ≈2.5x;
  Tinker Qwen3.8-27B = Hybrid+Vision 64K, current (not retired).

## Next steps (in order)
1. **Rerun Tinker smoke** (`13-1`, `51-12`) with current adapter — confirm clean JSON, no
   thinking leak, no truncation. Screen `tsmoke`, log `/tmp/tinker-smoke`.
2. If smoke passes → **full 400-task research-track run** with Qwen3.8-27B via Tinker.
3. **Attribution-guided repair** in `harness/pipeline.py`: replace blind ≤3-retry; on
   verifier failure send targeted repair prompt (what failed, why, smallest edit).
   Biggest documented lever (notes §2, §6a).
4. **Ask Adib**: does "Qwen-only" permit deterministic tooling (LibreOffice `soffice`
   recalculation) as pre-submission verifier? (Not model-related; WML uses it.)
5. Later: per-category skill/prompt-fragment library (retrieval-instructed beats direct).

## Process rules
- Before any harness change: check methodology-notes.md + source papers.
- Model calls only to *measure* against published hypotheses.
- Venue-first constraints still apply (`docs/CONSTRAINTS.md`): no dataset download,
  no LibreOffice, no docker build on this Mac.
