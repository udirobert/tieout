# Session status / handoff (updated 2026-09-05, A on standby)

Read `docs/TEAM-BRIEF.md` then this file.

## Headline (ship candidate)
`/tmp/tinker-400-hybrid` `--all --no-recalc`: **pass_rate 0.5475**, cell 0.48,
sheet 0.696, cell_acc 0.9545. Stitch: cell←`/tmp/tinker-400`, sheet←`/tmp/tinker-400-codegen`.
Pipeline default is now `--path hybrid` (no cross-path fallback). Never-blank kept.

## Ablation
- values-first `/tmp/tinker-400`: 46.75% / cell 48% / sheet 44%
- codegen-auto `/tmp/tinker-400-codegen`: 51.75% / cell 43.64% / sheet 69.6%
- hybrid stitch: **54.75%** / cell 48% / sheet 69.6%

## A status
C spec landed (task_0015): pin addresses only; sheet hybrid falls back to
values-first only when soffice reports `#ERR!` (silent skip on this Mac).
No new Tinker run — B owns the quota. Standby otherwise.
