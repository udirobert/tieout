# Devpost submission draft — tieout (Syndicate by Maximor)

Paste these fields into [https://syndicate-by-maximor.devpost.com/](https://syndicate-by-maximor.devpost.com/).
Update placeholders marked with `__...__` before submitting.

---

## Project name

tieout

## Tagline / one-liner

Every cell tied to its source — autonomous spreadsheet reconciliation for finance close.

## Track

Autonomous Office of the CFO

## What does your project do? (problem + solution)

Private markets and corporate finance teams still close books in Excel. Month-end tie-out, sub-ledger reconciliation, bank counterparty matching, and multi-entity consolidation are repetitive, error-prone, and scale by headcount — not by process.

tieout takes a workbook and a plain-English mandate, then:

1. Classifies the workflow (lookup, aggregation, sheet-level transform, consolidation).
2. Executes the transform using values-first or sandboxed Python/openpyxl codegen.
3. Verifies every answer cell — fatal formula errors and missing-lookups are blocked, not silently overwritten.
4. Retries with attribution-guided repair up to 3 times.
5. Routes unresolved or unmatched rows to a human-review exception queue with source-row evidence.
6. Emits the final workbook, `predictions.jsonl`, per-task `traces/<id>.jsonl`, and `exceptions.json`.

Accountants and controllers stay in the loop: read-only source data, approve-gated writes, and a full audit trail.

## How we used AO (Agent Orchestrator)

We used AO as the development control plane for tieout's Syndicate pivot. An AO orchestrator session broke the remaining work into focused worker tasks; __N__ worker sessions implemented the exception queue, Ylookup CFO demo fixtures, and Syndicate submission docs in isolated git worktrees. AO's Kanban tracked each session from task to implementation to merge.

The spreadsheet agent itself runs via Tinker at inference time; AO orchestrated the **engineering** of that agent for Track 2 (Office of the CFO). The demo video includes the AO dashboard with the total session count and a short clip of one worker session.

See `docs/SYNDICATE-AO-INTEGRATION.md` and `docs/AO-SESSION-LOG.md` for the full plan and session IDs.

## How does it work? (architecture + tools)

- **Pipeline:** `harness/pipeline.py` — classify → execute → verify → retry → exception queue.
- **Executor:** `harness/executor.py` — sandboxed Python with read-only source and API-key-stripped environment.
- **Verifier:** `harness/verifier.py` — missing graded cells, non-scalars, Excel errors, optional LibreOffice recalc gate.
- **Exception queue:** `harness/exceptions.py` — `write_exceptions()` and `review` CLI with evidence rows and approve/reject workflow.
- **Model:** Tinker Qwen/Qwen3.8-27B (no model weights in repo; `TINKER_API_KEY` from `.env`).
- **Demo fixtures:** `demo/close-tieout/` — Ylookup-anonymised bank counterparty, legal-entity mapping, and month-end movement reconciliation scenarios.

## Demo video URL

__TODO: upload 3–5 minute video and paste URL here.__

Video script: `docs/SYNDICATE-DEMO.md`

## GitHub repository

https://github.com/udirobert/tieout

## Try it / setup

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden

# live run (requires TINKER_API_KEY)
export TINKER_API_KEY= # set from .env
./demo/run_demo.sh close-tieout-bank-cp
```

Run exception review:
```bash
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

## Evaluation / measurable results

- General SpreadsheetBench Verified 400 regression: **68.00% pass rate** (272/400), 73.82% cell-level, 55.20% sheet-level, 400/400 tasks emit output. See `SUBMISSION.md` and `research/data/eval/clone_run/`.
- Syndicate CFO demo fixtures: `close-tieout-bank-cp`, `close-tieout-le-map`, `close-tieout-movements-rec` (`demo/README.md`).
- Exception queue: `exceptions.json` with per-cell evidence rows and approve/reject CLI (`harness/exceptions.py`).

## Team members

- __Name 1__ (__role__)
- __Name 2__ (__role__)
- __...__

Team captain: __name__

## Hackathon pass / social evidence

- Discord: joined and announced in `#showcase` (or equivalent): __TODO__
- LinkedIn / X post with hackathon pass, tagging @aoagents and Maximor: __TODO__

## Submission checklist

- [ ] Track selected: Autonomous Office of the CFO
- [ ] GitHub repo public: https://github.com/udirobert/tieout
- [ ] Demo video uploaded (3–5 min) and URL pasted above
- [ ] "How we used AO" paragraph filled with real session count
- [ ] All team members individually registered on Devpost
- [ ] One Devpost submission per team
- [ ] Hackathon pass posted to X or LinkedIn with required tags
- [ ] Discord participation confirmed

## Notes for judges

- Do not run `docker build` on a space-constrained Mac; use `./demo/run_demo.sh` or `harness/pipeline.py` directly.
- SpreadsheetBench scores are background validation, not the product demo. The demo should show a real CFO workflow on `demo/close-tieout/`.
- The Encode hackathon work (68% clone-run) is archived in `SUBMISSION.md`; the Syndicate pivot is in `docs/` and `demo/`.
