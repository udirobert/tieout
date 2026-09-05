# Session status / handoff (updated 2026-09-05, A on standby for 0003)

Read `docs/TEAM-BRIEF.md` then this file.

## Headline (ship candidate)
`/tmp/tinker-400-hybrid` `--all --no-recalc`: **pass_rate 0.5475**, cell 0.48,
sheet 0.696, cell_acc 0.9545. Stitch: cell←`/tmp/tinker-400`, sheet←`/tmp/tinker-400-codegen`.
Pin-scope is in the harness (codegen omits init values; values-first keeps them) but
the fresh 275-cell re-score did not clear ship.

## Ablation
- values-first `/tmp/tinker-400`: 46.75% / cell 48% / sheet 44%
- codegen-auto `/tmp/tinker-400-codegen`: 51.75% / cell 43.64% / sheet 69.6%
- hybrid stitch: **54.75%** / cell 48% / sheet 69.6%  ← **ship**
- hybrid-v2 pin-omit overlay: 52.75% / cell 45.09% / sheet 69.6%
- hybrid-pin (scoped, fresh cells): 51.75% / cell 43.64% / sheet 69.6%
- LoRA-v1: **32.25%** / cell 46.6 / sheet 0.8 — data-mix starvation of codegen completions; overtrained on 202 records
- WML: 74.67%

## A status
task_0018 done. Pin-scope is the serializer contract going forward. Ship unchanged.

## Measurement variance
Temp-0 rerun of identical values-first cells: 43.64% vs original 48.00% → ±3pp
run-to-run noise. Sub-2pp row differences in the ablation are within noise.
Promotion to new ship requires >noise-band win on the full 400.

## B status
LoRA-v1: 32.25% (sheet 0.8%) — negative; cause: codegen starvation + overtraining.
v2 in flight (log_v2b): 60/40 sheet:cell from 622 banked trajectories, 446 steps,
lr 5e-5, checkpoints every 25 steps. First v2 run crashed at step 222 (epoch-tiling
bug, fixed) but left a valid step-200 checkpoint
(tinker://0c3c3765-.../sampler_weights/000200) — subsample eval pending, may be
the sweet spot.

## C status
lora_v1 artifacts frozen in research/data/eval/lora_v1/ (+DIAGNOSIS.md: trailing
syntax drift). eval_checkpoints.py pre-staged. Open: reconcile 31.25% vs 32.25%
canonical v1 score; variance note landing in SUBMISSION.md; subsample-eval of the
v2 step-200 checkpoint.

## Ship container
Pin-scope contract (codegen omits init values; values-first keeps them) is
going-forward harness behavior, including in the ship container.
