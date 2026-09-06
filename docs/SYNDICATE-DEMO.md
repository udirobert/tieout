# Syndicate demo — 3-minute script + AO session log

**Track:** Autonomous Office of the CFO  
**Duration:** ≤5 min (aim for 3)  
**Audience:** Syndicate judges, Maximor team, Discord community

**Mandatory in video:** AO dashboard showing **total session count** used during the build (25% judging weight).

Do **not** show SpreadsheetBench scores in the demo. Show a **finance close workflow** on Ylookup fixtures (`demo/close-tieout/`).
Mention eval validation in one sentence at the end if time allows.

---

## Story spine

| Time | Beat | Visual | Narration (guide) |
|------|------|--------|-------------------|
| 0:00–0:20 | **Hook** | Fund/back-office imagery or spreadsheet grid | "Thirty trillion in private markets — and month-end close still happens in Excel. One wrong cell fails the tie-out." |
| 0:20–0:45 | **Pain** | `close-tieout-movements-rec` or `close-tieout-le-map` init workbook | "Fund-admin migration: map entities, reconcile movements before upload. Unmatched rows go to review." |
| 0:45–1:25 | **Agent run** | `./demo/run_demo.sh close-tieout-movements-rec` | "tieout takes the workbook and mandate. Classify, execute, verify every answer cell." |
| 1:25–1:50 | **Verification** | Verifier output: pass / `#N/A` flagged / fatal error blocked | "Fatal formula errors block commit. Unmatched lookups go to the exception queue — not silently overwritten." |
| 1:50–2:20 | **Human review** | `exceptions.json` — 2–3 rows with evidence | "The accountant sees exactly which source rows caused each flag. Approve or reject before the workbook is final." |
| 2:20–2:45 | **Improvement** | Before/after: failed lookup → skill added → pass | "When the same pattern fails again, we inject a domain skill from the failure trace. No retraining — the agent gets better on the next run." |
| 2:45–3:00 | **Close + AO** | **AO dashboard — session count visible** | "tieout — every cell tied to its source. Built with AO." |

---

## Demo commands (record these screens)

```bash
# 1. Build fixtures (once, ~44 KB — safe on space-constrained Mac)
python demo/build_fixtures.py

# 2. Run demo scenario
./demo/run_demo.sh close-tieout-movements-rec

# 3. Live agent (check Tinker credits first — docs/SYNDICATE-REQUIREMENTS.md)
export TINKER_API_KEY= # set from .env
python harness/pipeline.py \
  --dataset-dir demo/close-tieout \
  --out-dir /tmp/syndicate-demo \
  --path hybrid \
  --ids close-tieout-movements-rec \
  --fresh

# 2. Inspect trace (Neatlogs-friendly)
cat /tmp/syndicate-demo/traces/<scenario-id>.jsonl | tail -5

# 3. Review exceptions (human loop)
cat /tmp/syndicate-demo/exceptions.json
# python -m harness.exceptions review /tmp/syndicate-demo/exceptions.json
```

Fixtures: see `demo/README.md`. If demo dir is not yet populated, use a SpreadsheetBench
task reframed with CFO mandate text (lookup/consolidate category from `docs/TAXONOMY.md`).

---

## AO sessions (required — show in video)

Judges review demo video for AO usage. Record or screenshot AO for each phase below.
Update the **Status** column as you complete sessions.

| # | Session purpose | What AO built / decided | Status |
|---|-----------------|-------------------------|--------|
| 1 | Workflow mapping | CFO tie-out steps → harness stages; exception policy | pending |
| 2 | Syndicate docs | `SYNDICATE.md`, this file, `SYNDICATE-WORKFLOW.md` | done |
| 3 | Demo fixtures | Finance-framed workbooks in `demo/close-tieout/` | pending |
| 4 | Exception queue | Review UX + evidence rows on flagged cells | pending |
| 5 | Skill improvement | One lookup failure → `skills.py` fragment → re-run | pending |
| 6 | Demo video script | This storyboard + recording | in progress |

**In the video:** Include 5–10 seconds of AO session recording (screen capture of AO UI or
terminal with AO prompt visible). Narrate: *"We built this with AO — architecture, demo
scenarios, and the exception workflow."*

---

## What to show vs. skip

| Show | Skip |
|------|------|
| One realistic close scenario | Full 400-task eval run |
| Trace JSONL (1–2 lines) | Ablation table |
| Exception queue with evidence | LoRA / fine-tune story |
| One skill improvement example | Login, auth, deployment |
| AO session clip | Encode hackathon branding |

---

## Neatlogs (encouraged)

Syndicate partners recommend Neatlogs for agent trace/debug. If integrated:

- Import `traces/<id>.jsonl` into Neatlogs
- Show one failure → root cause → retry in the Neatlogs UI (30s clip)

If not integrated: raw JSONL in terminal is sufficient for demo.

---

## Devpost checklist

- [ ] Project title: **tieout**
- [ ] Track: **Autonomous Office of the CFO**
- [ ] Demo video URL (≤3 min)
- [ ] GitHub repo link
- [ ] "How we used AO" paragraph (from `SYNDICATE.md`)
- [ ] Tag Maximor / AO on social post with hackathon pass

**Deadline:** Sept 6, 18:00 GMT-4 (23:00 UTC+1)

---

## Fallback if demo fixtures incomplete

Use pipeline on a known lookup task from the eval suite, but **reframe on screen**:

- Rename instruction overlay: *"Sub-ledger tie-out: match entity URN to DFES number"*
- Show verifier + trace
- Narrate exception policy on `#N/A`

Do not mention SpreadsheetBench task IDs on screen.
