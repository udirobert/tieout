# Office of the CFO — workflow grounding for tieout

This document grounds tieout in specific finance operations. Syndicate Track 2 judges ask:
*Is this a genuine pain point? Is human judgment intuitive? Would accountants actually use it?*

Read this before the demo script (`SYNDICATE-DEMO.md`) or submission (`SYNDICATE.md`).

---

## Why spreadsheets, why close

Month-end close for funds and corporate finance still runs through Excel exports from ERP,
fund admin, and portfolio systems. The Office of the CFO does not lack software — it lacks
**flexible tie-out** on messy, one-off exports where every close has slightly different columns,
entity registers, and exception cases.

Private markets alone manage ~$30T AUM. When back-office capacity is tight, teams hire analysts
before they improve process. tieout targets the repetitive spreadsheet layer: lookups,
aggregations, filters, consolidations — with verification and human review on exceptions.

---

## Demo workflow (hero — record this)

**Fixture:** `close-tieout-bank-cp` · **Source:** Ylookup dataset 01 (`01-bank-statements-to-journal-entries`)

This is the **primary demo** for Syndicate. It comes from real anonymised client work: bank
statement rows staged for journal entry, counterparty pulled from truncated bank narratives,
matched against a vendor master list.

**Actors:** Treasury / fund accountant processing bank feeds  
**Trigger:** Weekly cash reconciliation or month-end bank close  
**Pain:** Bank writes names truncated, in capitals, wrapped mid-word. Master list has clean names.
52 of 100 rows in the source staging sheet had no counterparty match — **preserved by design**
in the anonymised dataset.

**Steps with tieout (demo):**
1. Workbook contains `Staging Sheet` + `Vendor Master List` + mandate in natural language
2. Agent matches column J (pulled counterparty) → column K (clean vendor name)
3. Verifier checks answer cells; **blank K = no match**
4. Unmatched rows → **`exceptions.json`** with evidence rows from source data
5. Accountant reviews: approve (keep blank / flag) or reject via CLI
6. Trace archived in `traces/close-tieout-bank-cp.jsonl`

**Demo command:** `./demo/simulate_demo.sh close-tieout-bank-cp` (offline) or `./demo/run_demo.sh close-tieout-bank-cp` (live Tinker).

Full script: `docs/SYNDICATE-DEMO.md`.

---

## Supported CFO workflows (product scope)

### Sub-ledger tie-out

**Actors:** Staff accountant or fund accountant  
**Trigger:** Month-end close, Day T+3 to T+10  
**Inputs:**
- GL trial balance export (CSV/XLSX)
- Sub-ledger or entity register (different column names, extra rows)
- Written mandate: which keys to match, which columns to populate, what to do with unmatched rows

**Steps today (manual):**
1. Import both files into a working workbook
2. Build INDEX/MATCH or XLOOKUP to pull GL balance into sub-ledger rows by entity ID
3. Add variance column; scan for `#N/A`, blanks, sign mismatches
4. Research exceptions line-by-line (missing entity in register, timing difference, mapping error)
5. Document adjustments; send exception list to controller for sign-off
6. Save final version for audit file

**Steps with tieout:**
1. Upload workbook + mandate (natural language: *"Match sub-ledger column L to URN lookup column K; populate DFES number in column B; flag unmatched rows."*)
2. Agent classifies as **lookup repair** → applies lookup skill fragment
3. Executes transform (values-first or codegen); verifier checks graded/answer cells
4. Unmatched rows (`#N/A`, key not found) → **exception queue** with source row evidence
5. Reviewer approves/rejects each exception; approved writes commit to output workbook
6. Trace JSONL archived for audit (model calls, verification status, tool output)

**Why this is realistic:** SpreadsheetBench taxonomy shows lookup repair as the dominant
cell-level bucket (VLOOKUP, INDEX-MATCH, OFFSET, conditional return). Real forum instructions
match fund-admin pain: *"consolidate data about schools using INDEX and MATCH… merge 15 columns
of data."*

**Demo fixture:** `close-tieout-le-map` (dataset 02 — entity mapping with `Corvus LE Reference` sheet).

---

## Secondary workflow: invoice / AP reconciliation

**Actors:** AP clerk, accounting manager  
**Trigger:** Weekly or month-end AP close  
**Inputs:** Invoice export (10k+ rows), PO reference sheet, mandate to filter/dedupe/sum

**Steps today:**
1. Filter rows (delete where column B first char not H/A; trim above first "Invoice No.")
2. Dedupe on vendor + invoice number; sum amounts
3. Match to PO lines; flag quantity or price mismatches
4. VBA macros break when export format shifts

**Steps with tieout:**
1. Mandate describes filter + dedupe + sum rules
2. Agent classifies as **sheet reorg** → sheet-level codegen path
3. Sandbox executes Python equivalent (never runs VBA in production)
4. Verifier + optional LibreOffice recalc catches `#REF!`, `#ERR!`
5. Mismatch rows → exception queue

Taxonomy: sheet-level bucket 1 — *"trim rows above first Invoice No."*, filter groups over
13k rows. Performance matters; harness uses read-only openpyxl and bottom-up deletes.

---

## Tertiary workflow: multi-entity consolidation

**Actors:** Consolidation accountant, controller  
**Trigger:** Quarter-end or fund-level reporting  
**Inputs:** Existing positions sheet, additions sheet, retirements sheet, target consolidated tracker

**Steps today:**
1. Net Existing + Additions − Retired by entity key
2. Hash-merge on composite keys (cols A+B+C); sum numeric columns
3. One wrong sign or key → consolidated NAV wrong

**Steps with tieout:**
1. Mandate: *"Net additions and retirements into Consolidated Tracker by entity ID."*
2. Agent classifies as **merge/dedupe/consolidate**
3. Set arithmetic across sheets; write verified values
4. Controller reviews variance exceptions before sign-off

Taxonomy: sheet-level bucket 2 — dict+array merge, multi-sheet net.

---

## Human judgment design

Judges ask whether the human side is intuitive. tieout follows three principles from
`docs/PATTERNS.md`:

### 1. Read-only by default
Agent never mutates source `/data`. All writes go to `/out`. Reviewer sees diff against init.

### 2. Evidence-backed exceptions
Every exception line cites the rows that caused it (source register row, lookup key, computed
variance). No black-box "something failed."

### 3. Approve-gated writes
Pipeline proposes; human confirms exceptions. Fatal errors block commit. Missing lookups follow
a **generalized policy** (not per-task id hacks): outer lookups that legitimately yield `#N/A`
for unmatched entities are flagged, not silently overwritten.

### Reviewer UX (demo scope)
No auth/login for hackathon demo. CLI or minimal JSON review file:

```
exceptions.json
  - task_id, cell, reason, evidence_rows[], proposed_value, status: pending|approved|rejected
```

Reviewer runs:

```bash
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

See `demo/README.md` and `docs/SYNDICATE-DEMO.md`.

---

## Agent improvement loop (cross-track credibility)

Track 2 is domain-first, but judges also care that the system is **agentic**, not a one-shot API.

tieout improves without retraining:

1. **Run** agent on task batch
2. **Cluster failures** by taxonomy bucket (`docs/TAXONOMY.md`: reasoning, serialization, parse/truncation)
3. **Inject skill** — add or refine fragment in `harness/skills.py` for that bucket
4. **Re-run** failed subset; measure delta

Encode weekend evidence: attribution-guided repair recovered 13% of blind retries vs weak
resampling; category skills target the 88% "reasoning" failure bucket. Demo shows one concrete
before/after on a lookup task.

Fine-tune (LoRA v1/v2b) was a negative result on Encode — documented in `SUBMISSION.md`.
Syndicate ship story is **skills + repair loop**, not weight updates.

---

## Eval suite mapping (SpreadsheetBench → CFO patterns)

| Taxonomy bucket | CFO workflow | Eval coverage |
|-----------------|--------------|---------------|
| Lookup repair | **Bank counterparty match** *(hero demo)* | Ylookup dataset 01 + 89+ MATCH/VLOOKUP eval tasks |
| Lookup repair | Sub-ledger tie-out | 89+ MATCH/VLOOKUP tasks |
| Multi-criteria aggregation | Cashflow matrices, SUMIFS close schedules | COUNTIF/SUMIF hits |
| Sheet filter / VBA equivalent | Invoice cleanup, row deletes | 55+ macro tasks |
| Merge/dedupe/consolidate | Entity consolidation | Multi-sheet net tasks |
| Date/time arithmetic | Accrual cutoffs, period filters | Date keyword tasks |

Full eval: 68% pass rate on 400 tasks (`research/data/eval/clone_run/`). Finance-subset
filtering: tasks whose instructions mention invoice, consolidat, reconcil, GL, ledger, fund.

---

## What accountants would still do

tieout does not replace judgment on:
- **Materiality** — which exceptions matter for sign-off
- **Policy** — new entity mappings, chart-of-accounts changes
- **Estimates** — accruals requiring management input
- **External confirm** — bank/custodian reconciliations outside the workbook

The agent handles the **mechanical tie-out**; the accountant handles **exceptions and sign-off**.

---

## References

- Anthropic: [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- Anthropic: [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- Maximor: https://www.maximor.ai/
- Internal: `docs/TAXONOMY.md`, `harness/skills.py`, `harness/verifier.py`
