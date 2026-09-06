# Session status — Syndicate pivot (2026-09-06)

**Active event:** Syndicate by Maximor · Track 2: Autonomous Office of the CFO  
**Deadline:** Sept 6, 18:00 GMT-4 (23:00 UTC+1)  
**Read first:** `SYNDICATE.md` → `docs/SYNDICATE-DEMO.md` → `docs/SYNDICATE-WORKFLOW.md`

Encode hackathon is complete (68% ship). This file tracks Syndicate submission work.

---

## Syndicate checklist

| Item | Status | Notes |
|------|--------|-------|
| Submission doc | **done** | `SYNDICATE.md` |
| CFO workflow grounding | **done** | `docs/SYNDICATE-WORKFLOW.md` |
| Demo script + AO log | **done** | `docs/SYNDICATE-DEMO.md` |
| Syndicate requirements checklist | **done** | `docs/SYNDICATE-REQUIREMENTS.md` (space, AO, credits, Devpost) |
| Demo fixtures (`demo/close-tieout/`) | **done** | 3 tasks, 44 KB — `python demo/build_fixtures.py` |
| Exception queue (`exceptions.json` + review) | **pending** | Human loop for demo |
| Skill improvement example (1 before/after) | **pending** | For demo beat 2:20–2:45 |
| AO sessions recorded (≥5 in demo video) | **pending** | Update AO table in SYNDICATE-DEMO.md |
| 3-min demo video | **pending** | Do not lead with SpreadsheetBench scores |
| Devpost submission | **pending** | https://syndicate-by-maximor.devpost.com/ |

---

## What we're shipping (Syndicate story)

**Product:** Autonomous spreadsheet reconciliation for finance close — tie-out, AP recon,
consolidation — with verify, exception routing, and audit traces.

**Not the demo:** Encode ablation table, fine-tune post-mortem, thinking-on vs off insight.

**Validation (background):** 68% on SpreadsheetBench Verified 400 (`research/data/eval/clone_run/`).

**Demo path:** `harness/pipeline.py --path hybrid` (repair + skills), not `clone_run.py`.

---

## Encode archive (completed)

<details>
<summary>Container validated, clone-run ship — click to expand</summary>

### ✅ Container validated (2026-09-06, pre-09:00)
- Image built from pushed repo (10.4GB; torch+CUDA wheels dominate). Entrypoint is `harness/clone_run.py` with the fsync + `os._exit(0)` clean-exit fix; failure path exits 1 with traceback.
- **Smoke (2 tasks) passed three times over**, final run on the pushed repo: both tasks `ok`, full contract written (`predictions.jsonl`, `outputs/`, `traces/`, `run.log`), container exits cleanly (`--rm` reaped it). The tinker-poller hang found in the first dry-run is fixed.
- **Full-400 unattended container run COMPLETED and scored**: 400/400 graded, clean exit, **67.75%** (271/400) with the official scorer — reproduces the clone-run ship score (68.00%) within the noise band. Cell 75.64% / sheet 50.40% / cell_acc 37.00%. Audit: 34 json_err / 23 trunc / 366 ok. Artifacts in `research/data/eval/container400/`. task_0020 **done**.
- Judges' turnkey `docker run` invocation documented in SUBMISSION.md ("Judges' run" section).
- Gotcha for anyone rebuilding: `.dockerignore` must NOT exclude `research/baseline/` (`clone_run.py` imports `common.py` from there — the build fails with "COPY failed" if excluded). Fixed and pushed.

### ⚠ Ship call: clone-run promoted (2026-09-05, ~22:30)
- **Clone-run promoted to ship headline**: 68.00% / 272/400, cell 73.82%, sheet 55.20%, cell_acc 37.09%.
- Old hybrid 54.75% superseded; stays in the ablation table as the harness-gap finding (same model, thinking off, wrong decode path).
- Container entry must be `harness/clone_run.py`, NOT `pipeline.py` (which runs the old hybrid). Anyone rebuilding the image: replace the entrypoint and rebuild before the dry-run.
- **Cell-accuracy trade-off**: 37.09% on clone-run vs 95.45% on old hybrid — thinking-on gets more tasks fully right but produces partial / truncated outputs on a long tail (33 JSONDecodeError + 25 trunc, 23 overlap). Documented in SUBMISSION.md "The cell-accuracy trade-off".

### Strategic re-baseline (still relevant — read first)
- Official Qwen3.8-27B one-shot floor is **59.0%**. Clone-run ship is **+9pp over the floor, +21.25pp over the 46.75% internal baseline, +13.25pp over the old hybrid**. The harness gap is closed; the lift is decode-path, not prompt or parser.
- Judges score the container on a **holdout set**: id-keyed artifacts are worthless there; all shipped behavior must be generic. `task_0022` (de-id-keying) is **done** — `#N/A` is a general missing-lookup policy in SUBMISSION.md; no per-id whitelist.
- Promotion bar vs ship: ≥70.00% full-400 / ≥66.0% on the 100-subsample (±2–3pp noise band documented in SUBMISSION.md + RESULTS_CHECKLIST.md).

### Headline (eval artifact)
`/tmp/clone-run-400` `--all --no-recalc`: **pass_rate 0.68** (272/400), cell **0.7382**,
sheet **0.552**, cell_acc 0.3709. `qwen3_5` thinking on, official prompt, our parse/write.
Old hybrid 54.75% is superseded (harness-gap: thinking off).

Full Encode session log: expand above or see git history for `docs/SESSION-STATUS.md` pre-pivot.

</details>

---

## Next actions (priority order)

1. Populate `demo/close-tieout/` with 1–2 finance-framed workbooks (from your datasets)
2. Wire exception queue output on verify failures
3. Record one skill-improvement before/after for demo
4. Run AO sessions for fixtures + exception queue; update AO table
5. Record 3-min demo video per `docs/SYNDICATE-DEMO.md`
6. Submit Devpost before deadline
