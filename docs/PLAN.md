# Plan — split to maximize win probability

Primary metric is pass_rate over all 400. One wrong graded cell = failed task.
Reliability (code-exec + verify) beats clever prompting.

## Roles (3–4 people, independent axes)

- P1 Harness/loop: classify (cell/sheet, formula/value/VBA) → Qwen writes openpyxl Python
  → exec in-container → verify second way (re-read after write / pandas vs formula) → retry ≤3.
  Always best guess, never blank. Owns `traces/<id>.jsonl` (one line per model call, keep failures
  with `error` set — golden value with no reasoning = disqualify).
- P2 Fine-tune (Tinker): starts at team-forming, queued invite first. Trains on task-type-diverse
  + synthetic variations (varied layouts, fund-style sheets: NAV, capital calls), NOT just the 400.
  Private holdout punishes overfit. Ends by running best harness on fine-tuned checkpoint
  (`tinker://<run-id>/sampler_weights/final` via `tinker_predict.py`).
- P3 Taxonomy: triage baseline failures by instruction_type early (VBA, lookup, pivot-agg,
  ambiguous NL, formatting-dependent). Tells P1/P2 where 59% breaks. Feeds write-up table.
- P4 Container/submission (or P1-double): owns Dockerfile + `/data:/out` contract from hour one.
  Tests unattended start Sat afternoon. Owns full-400 run, `results.json`, SUBMISSION.md.

2-person fallback: P1+harness+container, P2+finetune+taxonomy.

## Sequencing

Sat 10:00 brief → taxonomy sample + harness v0 + container boots + Tinker queued.
Sat afternoon: harness with code-exec beats baseline on subset, image builds.
Sun morning: full 400, swap in finetune checkpoint under same harness, freeze image.
Sun 12:00: repo URL via form. Judging 12:00–16:00. `items` must be 400 with `--all`.

## Write-up

`SUBMISSION.md` (150–300 words) + models (exact ids / tinker:// paths, training data,
were goldens in it?, steps/LR/compute/wall time) + `results.json` summary block.
Interesting method with no write-up loses points.
