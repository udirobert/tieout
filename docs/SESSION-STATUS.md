# Session status / handoff (updated 2026-09-05, A in charge)

Fresh-context handoff. Read `research/methodology-notes.md` first, then
`docs/TEAM-BRIEF.md` (board + roles), then this file for state.

## Goal
Beat 59.0% baseline on SpreadsheetBench Verified 400 with Qwen3.8-27B via Tinker.

## State
- **A owns `harness/*.py` exclusively.** Codegen loop + write-path fixes + soffice
  post-check + `--path` / `--temperature` are in. task_0001 and task_0009 done.
- **`ts400` finished** on this Mac (`/tmp/tinker-400`): 400 lines, pass_rate
  **0.4675**, cell 0.48 / sheet 0.44, 373 harness-ok / 14 partial / 13 error.
  That is the no-repair values-first number (old code). Below the 59.0% published
  one-shot floor — C should confirm recalc vs `--no-recalc`.
- **A smoke (task_0007) in progress** — both paths on `13-1` + `51-12` via Gemini
  on `tieout-builder` (dataset lives there).
- **MergedCell write crash fixed** (task_0010).
- **C hook**: `skills/library.py` `fragment_for` is wired; stub returns "".
- **`.env`**: GEMINI_API_KEY had a missing newline. Fixed locally, not committed.

## Next (A)
1. Write-path + skills committed (task_0011/0012). Re-run 20-id gate, then `/tmp/tinker-400-codegen`.
2. 13-1 Qwen vs Gemini gap stays in the ablation table — B's fine-tune, not a harness patch.
3. B: Modal / acct #2 `--temperature 0.7`. A uses Tinker #1 at concurrency 4 for the 400.

## Process rules
- Before any harness change: methodology-notes.md + source papers.
- Model calls only to measure a published hypothesis.
- No dataset download / LibreOffice / docker build on this Mac.
