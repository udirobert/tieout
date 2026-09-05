# SpreadsheetBench Methodology Notes (research-backed)

> Sources verified 2026-09-05. Goal: stop trial-and-error; adopt published best practice.

## 1. Qwen3.8-27B thinking-mode (root cause of the `<think>` leak — SOLVED, documented)
Source: Qwen docs (qwen.readthedocs.io, Quickstart).
- Hard switch: pass `enable_thinking=False` to `apply_chat_template(...)` — this is the
  documented way to get non-thinking output from hybrid Qwen3 models. We render the chat
  template ourselves, so this works through Tinker unchanged.
- `/no_think` soft switch exists but docs recommend the hard switch when thinking is not
  desired at all.
- Output headroom: Qwen team recommends `max_new_tokens` up to 16384 for complex tasks
  (CoT happens implicitly even in instruct models); our 8192 cap risks truncation → raise.
- Sampling defaults: temperature=0.7, top_p=0.8, top_k=20, min_p=0 (for Instruct-2507).
- Note: Thinking-2507 variants emit a bare `</think>` with no opening tag — if we ever
  support thinking, parse on `</think>`, not `<think>`.

## 2. SpreadsheetBench paper (arXiv:2406.14991, NeurIPS 2024 spotlight)
- Inference settings evaluated: single-round direct < single-round retrieval-instructed
  < multi-round retrieval-instructed with **executed feedback**. Execution feedback in the
  loop was the biggest lever in their ablations.
- Known failure modes: complex/compositional instructions, robustness to unseen values
  (their online-judge multi-testcase design exists precisely because one-shot value
  answers are brittle), and spreadsheet serialization quality.
- GPT-4-class models were in the low double digits single-round — 59% baseline means the
  400-task "Verified" track with a modern model is the real game; headroom is large.

## 3. WML (arXiv:2607.20999) — directly on our benchmark
- Evaluated on `spreadsheetbench_verified_400` — the exact 400-task research track.
- Architecture that reached 74.67 (Qwen3.6-Flash) / 90.33 (DeepSeek) Hard Accuracy:
  1. Reusable "skill" package per workflow node (procedural knowledge, not per-task hacks).
  2. Execution feedback via **LibreOffice recalculation (`soffice`)** as the evaluator.
  3. Attribution-guided repair: identify the failed workflow node/mechanism, apply the
     smallest valid edit, re-verify (not blind full retries).
  4. Compiled execution sharply cut tokens/calls vs. direct agent while keeping wins.
- "Hard Accuracy" = all test cases pass (their grading ≈ our verifier philosophy).
- Repro protocol: seed-42 fixed splits, 3 seeds, mean±std — useful for our runs.

## 4. Implications for tieout (concrete changes)
1. adapters.py: add `enable_thinking=False` to `apply_chat_template`; raise max_tokens.
2. Replace blind ≤3-retry with **attribution-guided repair**: on sanity_check/verifier
   failure, send back a *targeted* repair prompt (what failed, why, smallest edit) —
   mirrors SheetAgent/WML; blind resampling is the documented weak baseline.
3. Consider `soffice --headless --convert-to xlsx` recalculation as a pre-submission
   verifier when tasks involve formulas (WML's evaluator), if the rules allow — flag
   for Adib: does "Qwen-only" permit deterministic tooling like LibreOffice? (Benchmarks
   allow it; it's not a model.)
4. Build a small reusable "skill"/prompt-fragment library per task category (sheet
   manipulation patterns) instead of one monolithic prompt — retrieval-instructed beats
   direct in the paper's ablations.
5. Evaluation hygiene: fixed task ordering/seeds, log latency (done), report mean±std
   on repeatable subsets where budget allows.

## 5. SheetAgent (arXiv:2403.03636, WWW 2025 oral) — background
Planner/Informer/Retriever decomposition with iterative task reasoning + reflection gave
20–40% pass-rate gains over baselines on long-horizon spreadsheet tasks. Confirms
decompose → inspect → act → reflect loop over one-shot generation.

## Process rule going forward
Before any harness change: check this file + source papers first. Only run model calls
to *measure* against a published hypothesis, never to discover what a README already
documents.
