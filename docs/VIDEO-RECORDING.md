# Demo video recording guide — tieout (Syndicate by Maximor)

**Goal:** 3–5 minute video (aim 3:30) that shows a real Office-of-the-CFO workflow, the exception queue, and the AO dashboard. Use `close-tieout-bank-cp` as the hero scenario. Do **not** lead with SpreadsheetBench scores.

**Tools:** QuickTime Player (Screen Recording) or OBS. Use a clean terminal at ~120×40. Keep font large (≥16 pt) for readability. Record audio or add a voice-over later.

**Output file:** `tieout-syndicate-demo.mp4` (≤500 MB).

---

## Before recording

1. **Reset the demo output:**
   ```bash
   rm -rf /tmp/syndicate-demo
   ```
2. **Stage the terminal:**
   ```bash
   cd /Users/udingethe/Dev/tieout
   clear
   ```
3. If using AO, open the AO desktop app and the **session count** view so you can cut to it at 2:40.
4. Optional: have `demo/close-tieout/spreadsheet/close-tieout-bank-cp/1_close-tieout-bank-cp_init.xlsx` open in Excel/Numbers to show the init sheet for the scenario beat.

---

## Shot list & narration

### Shot 0 — Title card (0:00–0:05)

Display a simple title slide or terminal banner:

```
tieout — every cell tied to its source
Autonomous spreadsheet reconciliation for finance close
Syndicate by Maximor · Track 2: Autonomous Office of the CFO
```

### Shot 1 — Hook (0:05–0:25)

**Visual:** Your face / voice-over, or a short screen recording of an Excel spreadsheet with rows of bank transactions.

**Narration:**
> "Private markets NAV takes six or seven rounds with administrators — numbers that don't foot, side letters wrong. Month-end close still happens in Excel. One wrong cell fails the tie-out. tieout is an autonomous spreadsheet reconciliation agent for the Office of the CFO. Every cell tied to its source."

### Shot 2 — Scenario (0:25–0:45)

**Visual:** Open `demo/close-tieout/spreadsheet/close-tieout-bank-cp/1_close-tieout-bank-cp_init.xlsx` and show columns J (Pulled Out Sender/Beneficiary) and K (blank). Then show the `Vendor Master List` sheet.

**Narration:**
> "Here's a bank statement staging sheet. Column J has the pulled counterparty strings from the bank. Column K is empty. The agent has to match each one to the vendor master list — and if it can't find a clean match, it must leave it blank. Those rows go to the exception queue for the accountant."

### Shot 3 — Run the agent (0:45–1:25)

**Visual:** Terminal. Run the offline demo. No Tinker key needed.

```bash
./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden
```

Expected output to appear on screen:

```
=== simulate_demo: close-tieout-bank-cp (golden) ===
Output:     /tmp/syndicate-demo/outputs/close-tieout-bank-cp.xlsx
Exceptions: 2
Queue:      /tmp/syndicate-demo/exceptions.json

  Staging Sheet!K5 | empty answer cell | proposed=''
    evidence: Staging Sheet row 2 key='NI ABF II SCSP'
    evidence: Staging Sheet row 2 key='240-149813-030'
  Staging Sheet!K13 | empty answer cell | proposed=''
    ...
```

**Narration:**
> "tieout takes the workbook and the mandate. It classifies the task, executes the match, and verifies every answer cell. Two rows have no match — not silently overwritten, preserved as exceptions."

### Shot 4 — Exceptions (1:25–1:50)

**Visual:** Terminal. Show the exception queue.

```bash
cat /tmp/syndicate-demo/exceptions.json
```

Or `jq` for pretty display:

```bash
cat /tmp/syndicate-demo/exceptions.json | jq '.exceptions[] | {cell, reason, evidence_rows}'
```

**Narration:**
> "The exception queue gives the accountant the cell, the reason, and source-row evidence. The source data stays read-only; the agent proposes, the human decides."

### Shot 5 — Human review (1:50–2:20)

**Visual:** Terminal. Run the review CLI. Approve one exception and reject the other.

```bash
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

When prompted:
- For `K5`: type `y` (approve, leave blank).
- For `K13`: type `n` (reject, reverts to init value).

Then show the updated file:

```bash
cat /tmp/syndicate-demo/exceptions.json | jq '.exceptions[] | {cell, status}'
```

**Narration:**
> "The accountant sees exactly which source rows caused the flag. Approve or reject before the workbook is final. Only approved exceptions are written to the final workbook."

### Shot 6 — Skill loop (2:20–2:40)

**Visual:** Terminal. Run the skill demo.

```bash
./demo/run_skill_demo.sh
```

**Narration:**
> "When the same pattern fails again, we add a domain skill — no retraining. Lookup and reconciliation skills are injected from the instruction."

### Shot 7 — AO dashboard (2:40–3:00)

**Visual:** AO desktop. Scroll the session list and show the **total session count**.

**Narration:**
> "This Syndicate pivot was built with Agent Orchestrator — an orchestrator session planned the work, worker sessions implemented the exception queue, demo fixtures, and docs. The dashboard shows the total session count."

### Shot 8 — Close (3:00–3:15)

**Visual:** Back to title card or terminal banner.

**Narration:**
> "tieout — every cell tied to its source. Validated on four hundred real spreadsheet tasks. Built for the Office of the CFO."

---

## Optional beats

- **Trace:** show one line of `traces/close-tieout-bank-cp.jsonl`.
  ```bash
  cat /tmp/syndicate-demo/traces/close-tieout-bank-cp.jsonl | tail -1 | jq
  ```
- **Live run:** if you have Tinker credits, replace Shot 3 with `./demo/run_demo.sh close-tieout-bank-cp`.
  ```bash
  export TINKER_API_KEY= # set from .env
  ./demo/run_demo.sh close-tieout-bank-cp
  ```

---

## Post-production checklist

- [ ] Video is 3–5 minutes.
- [ ] Audio is clear or captions are added.
- [ ] AO dashboard session count is visible for at least 5 seconds.
- [ ] No SpreadsheetBench scores in the first 2 minutes (one closing line is fine).
- [ ] Uploaded to YouTube / Vimeo / Devpost video field.
- [ ] URL pasted into `docs/DEVPOST_SUBMISSION.md` and submitted to Devpost.
