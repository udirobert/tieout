# tieout — Every cell tied to its source.

Autonomous spreadsheet reconciliation for finance close.  
**Syndicate by Maximor** — Track 2: Autonomous Office of the CFO (Sept 5–6, 2026).

Given a workbook + natural-language mandate, tieout executes the transform, verifies every
answer cell, routes exceptions to human review, and archives a full audit trace.

**Submission:** `SYNDICATE.md` · **Demo script:** `docs/SYNDICATE-DEMO.md` · **Checklist:** `docs/SYNDICATE-REQUIREMENTS.md` · **Doc index:** `docs/DOC-INDEX.md`  
**Devpost:** https://syndicate-by-maximor.devpost.com/

---

## The problem

Month-end close, sub-ledger tie-out, invoice reconciliation, and multi-entity consolidation
still happen in Excel. One wrong cell fails the deliverable. tieout automates the mechanical
layer — lookups, aggregations, filters, consolidations — with verification and approve-gated
exceptions for the accountant.

See `docs/SYNDICATE-WORKFLOW.md` for workflow grounding (bank counterparty match — hero demo,
sub-ledger tie-out, AP recon, consolidation).

---

## Quick start (demo)

```bash
# Build fixtures from ~/Downloads/Ylookup Hackathon Datasets (~44 KB, space-safe)
python3 demo/build_fixtures.py

# Hero demo — offline (no Tinker; produces exceptions.json)
./demo/simulate_demo.sh close-tieout-bank-cp

# Live agent — check Tinker credits first (docs/SYNDICATE-REQUIREMENTS.md)
export TINKER_API_KEY= # set from .env
./demo/run_demo.sh close-tieout-bank-cp

# Human review after run
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Env: `TINKER_API_KEY` (required), `GEMINI_API_KEY` (optional), `SOFFICE` (optional LibreOffice recalc).

---

## Validation (eval suite)

SpreadsheetBench Verified 400 is our **regression harness**, not the product demo.

| Run | pass_rate | cell_accuracy | Where |
|-----|-----------|---------------|-------|
| **Eval (clone-run)** | **68.00%** (272/400) | **37.09%** | `research/data/eval/clone_run/` |
| Container reproduction | 67.75% (271/400) | 37.00% | `research/data/eval/container400/` |

Encode hackathon write-up and ablation table: `SUBMISSION.md`.

---

## Layout

```
tieout/
  SYNDICATE.md           Syndicate submission (Track 2 — read this first)
  SUBMISSION.md          Encode hackathon archive (ablation + scores)
  demo/                  Finance close demo fixtures (Syndicate)
  harness/               Agent pipeline: classify → execute → verify → retry
  docs/
    SYNDICATE-WORKFLOW.md   CFO workflow grounding (bank-cp hero)
    SYNDICATE-DEMO.md       3-min demo script + AO session table
    SYNDICATE-REQUIREMENTS.md  Devpost checklist, judging weights
    TAXONOMY.md             Failure buckets → skill categories
    HACKATHON-NOTES.md      Encode retro (concurrency, repair loop, factorial evals)
  research/              UPSTREAM SpreadsheetBench starter (read-only)
  research/data/eval/    Eval artifacts (clone_run, container400, …)
  Dockerfile             Batch container (/data ro → /out)
```

---

## Agent pipeline

```
classify → (cell: values-first | sheet: codegen) → exec → verify → retry (≤3) → exception queue
```

- **Demo path:** `harness/pipeline.py --path hybrid` (repair loop + skills)
- **Eval path:** `harness/clone_run.py` (one-shot values-first, 68% headline)
- **Skills:** `harness/skills.py` — lookup, aggregation, consolidation, date arithmetic
- **Traces:** `traces/<id>.jsonl` — audit trail (Neatlogs-friendly)

Details: `harness/README.md`

---

## Built with

AO · Python · openpyxl · Tinker (Qwen3.8-27B) · Neatlogs (traces)

All Syndicate work documented in `SYNDICATE.md` → "How we used AO".

---

## Prior work

- **Encode × Ylookup hackathon** (Sept 5–6, 2026): SpreadsheetBench research track, 68% ship.
  [Demo video](https://x.com/UNgethe/status/2096550517878989285) ·
  [Write-up (Medium)](https://medium.com/@ungethe/nine-points-then-we-trained-0bb2784446fc)
