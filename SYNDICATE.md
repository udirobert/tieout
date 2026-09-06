# Syndicate by Maximor — Submission: tieout

**Track:** Autonomous Office of the CFO  
**Event:** Syndicate by Maximor (5–6 September 2026)  
**Devpost:** https://syndicate-by-maximor.devpost.com/  
**Repo:** https://github.com/udirobert/tieout

---

## Elevator pitch

**tieout** automates spreadsheet reconciliation for finance close — the work accountants
still do in Excel when tying sub-ledgers to the GL, consolidating entities, and preparing
audit support. Given a workbook and a natural-language mandate, the agent executes the
transform, verifies every answer cell against source data, routes exceptions to a human
reviewer, and leaves a full audit trace.

Every cell tied to its source.

---

## The CFO pain point

Private markets and corporate finance teams close books in spreadsheets. Month-end tie-out,
sub-ledger reconciliation, invoice matching, and multi-entity consolidation are repetitive,
error-prone, and scale by headcount — not by process.

| Workflow | What breaks today | tieout's role |
|----------|-------------------|---------------|
| **Sub-ledger tie-out** | Manual INDEX/MATCH across entity registers and GL exports; unmatched rows discovered late | Agent resolves lookups, flags `#N/A` and unmatched keys for review |
| **Invoice / AP reconciliation** | Filter, dedupe, and sum across 10k+ row exports; VBA macros that break on format changes | Agent implements equivalent transforms in sandboxed Python; verifier catches fatal formula errors |
| **Multi-sheet consolidation** | Net additions/retirements across sheets into a consolidated tracker; one wrong cell fails the deliverable | Agent writes verified values; human approves exceptions before commit |
| **Audit support prep** | No trace of who changed what or why a cell value was chosen | Every run produces `traces/<task>.jsonl` with model calls, tool output, and verification status |

These are genuine Office-of-the-CFO workflows — not consumer banking, trading, or payments.
Spreadsheets are where close still happens for funds and mid-market finance teams.

---

## What we built

```
Workbook + mandate
       │
       ▼
┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Classify     │───▶│ Execute     │───▶│ Verify +     │───▶│ Exception   │
│ (lookup /    │    │ (values or  │    │ recalc gate  │    │ queue for   │
│  agg / sheet)│    │  codegen)   │    │ (≤3 retries) │    │ human review│
└──────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
       │                   │                   │                    │
       └───────────────────┴───────────────────┴────────────────────┘
                                    │
                                    ▼
                          traces/ + predictions.jsonl
                          (audit trail for every run)
```

**Core loop** (`harness/pipeline.py`): classify task type → route to values-first (cell-level)
or codegen (sheet-level) → sandbox exec → sanity verify → optional LibreOffice recalc gate →
attribution-guided repair (≤3 attempts) → never blank (always emit workbook + trace).

**Human judgment** is first-class, not bolted on:

- Writes are **approve-gated** in product demos: agent proposes; reviewer confirms exceptions
- **Exception queue** carries evidence rows (source data that caused the flag)
- Fatal formula errors (`#REF!`, `#ERR!`, `#VALUE!`) block silent commit; missing-lookup
  tokens (`#N/A`) follow a generalized policy — legitimate unresolved references are flagged,
  not auto-corrected

**Skill memory** (`harness/skills.py`): category-specific prompt fragments (lookup, aggregation,
consolidation, date arithmetic) selected from instruction text. Failed runs feed the taxonomy
(`docs/TAXONOMY.md`); new skills can be injected and re-evaluated — the agent improves on
recurring patterns without retraining the base model.

---

## How we used AO

All Syndicate work was built with **AO** (Agent Orchestrator). Judges: AO session recordings
appear in the demo video and in `docs/SYNDICATE-DEMO.md`.

| Phase | AO role |
|-------|---------|
| **Workflow design** | Mapped Office-of-the-CFO close steps to harness stages; drafted exception-routing policy |
| **Harness wiring** | Connected classify → execute → verify → retry loop; integrated skills library |
| **Demo scenarios** | Built finance-framed workbook fixtures and mandate text from our datasets |
| **Eval suite** | Wired SpreadsheetBench Verified 400 as regression harness (background validation) |
| **Documentation** | This submission pack, demo script, workflow grounding doc |
| **Demo video** | Script and storyboard; AO sessions referenced in walkthrough |

---

## Validation (eval suite — not the product)

We validated generalization on **SpreadsheetBench Verified 400** — 400 real forum-style
spreadsheet tasks (275 cell-level, 125 sheet-level). This is our regression suite, not the
demo judges watch.

| Metric | Score | Notes |
|--------|-------|-------|
| Pass rate (primary) | **68.00%** (272/400) | Config-parity clone run |
| Cell-level pass | 73.82% (203/275) | Lookups, aggregations |
| Sheet-level pass | 55.20% (69/125) | Filters, consolidations |
| Reliability | 400/400 items, 0 missing | Never-blank contract |

Finance-relevant task patterns in the eval suite (from taxonomy probe): VLOOKUP/INDEX-MATCH
(89+ tasks), SUMIF/COUNTIF aggregation (13+), invoice/filter/consolidate sheet transforms
(55+ macro/VBA-equivalent). See `docs/TAXONOMY.md` and `docs/SYNDICATE-WORKFLOW.md`.

Prior Encode hackathon write-up and ablation table: `SUBMISSION.md` (archived).

---

## Demo (what judges watch)

**Duration:** ≤5 min (aim for 3; Devpost allows 3–5)  
**Script:** `docs/SYNDICATE-DEMO.md`  
**Checklist:** `docs/SYNDICATE-REQUIREMENTS.md`

Video must show **AO dashboard with total session count** (25% AO usage + 15% demo criteria).

1. **Hook** — $30T private markets; close still happens in Excel
2. **Scenario** — Sub-ledger tie-out or invoice reconciliation workbook + mandate
3. **Agent run** — classify → execute → verify; show trace (Neatlogs-friendly JSONL)
4. **Exception queue** — 2–3 flagged rows with source evidence; reviewer approves
5. **Improvement loop** — one failed lookup category → skill injected → re-run passes
6. **Close** — tieout · every cell tied to its source · built with AO

Demo fixtures: `demo/` (see `demo/README.md`).

---

## Run it

```bash
# Demo scenario (finance close fixture)
python harness/pipeline.py --dataset-dir demo/close-tieout --out-dir /tmp/tieout-demo \
  --path hybrid --ids <scenario-id>

# Full eval suite (regression — requires SpreadsheetBench dataset mount)
python harness/pipeline.py --dataset-dir /data --out-dir /out --path hybrid

# Docker (unattended batch)
docker build -t tieout .
docker run --rm --env-file keys.env \
  -v /path/to/data:/data:ro \
  -v /path/to/out:/out \
  tieout
```

Env: `TINKER_API_KEY` (required), `GEMINI_API_KEY` (optional spare), `SOFFICE` (optional LibreOffice recalc).

---

## Cost, speed, reliability

| Dimension | Current | Direction |
|-----------|---------|-----------|
| **Accuracy** | 68% pass on 400-task eval suite | Finance-subset eval + skill injection on failure categories |
| **Reliability** | Never blank; verifier + recalc gate | Exception routing prevents silent bad commits |
| **Cost** | ~$0.0X per task via Tinker (model-dependent) | Category skills reduce retry count |
| **Speed** | Sequential ~35s mean latency per task | Async fan-out planned (see `docs/HACKATHON-NOTES.md`) |

Temp-0 inference carries ±2–3pp run-to-run variance; promotion requires beating prior best by
more than the noise band.

---

## What we deliberately did not build

Per Syndicate guidance: no login/auth/2FA (not core to the workflow). No consumer banking
features. No fine-tune-as-headline (Encode post-mortem: inference config beat LoRA on the
same model). SpreadsheetBench scores are validation evidence, not the demo story.

---

## Links

| Resource | Location |
|----------|----------|
| **Devpost checklist + space/credits** | `docs/SYNDICATE-REQUIREMENTS.md` |
| CFO workflow grounding | `docs/SYNDICATE-WORKFLOW.md` |
| Demo script + AO log | `docs/SYNDICATE-DEMO.md` |
| Failure taxonomy | `docs/TAXONOMY.md` |
| Harness README | `harness/README.md` |
| Encode archive (ablation) | `SUBMISSION.md` |
| Eval artifacts | `research/data/eval/clone_run/` |

---

## Team

- Team name: tieout
- Track: **Autonomous Office of the CFO**
- Built with: AO, Python, openpyxl, Tinker (Qwen3.8-27B), Neatlogs (traces)
