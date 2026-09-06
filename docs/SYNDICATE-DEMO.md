# Syndicate demo — script, commands, AO log

**Track:** Autonomous Office of the CFO  
**Duration:** ≤4 min (aim for 3:30)  
**Hero fixture:** `close-tieout-bank-cp` (Ylookup dataset 01 — bank counterparty match)  
**Audience:** Syndicate judges, Maximor team, Discord

**Mandatory in video:** AO dashboard with **total session count** (25% AO + 15% demo criteria).

**One story only:** Real fund-admin spreadsheet data → agent proposes → exceptions with evidence →
human approves → built with AO. Do **not** show SpreadsheetBench scores except one closing line.

---

## Wedge (say once)

> Real anonymised fund-admin data. Verification-first — never silent commit. Unmatched rows
> route to humans with evidence, not auto-fixed. Every cell tied to its source.

Ylookup datasets preserve deliberate unmatched rows — same counts before and after anonymisation.
That is the product, not a bug.

---

## Story spine

| Time | Beat | Visual | Narration |
|------|------|--------|-----------|
| 0:00–0:25 | **Hook** | Spreadsheet / fund imagery | "Private markets NAV takes six or seven rounds with administrators — numbers that don't foot, side letters wrong. Month-end close still happens in Excel. One wrong cell fails the tie-out." *(paraphrase call-1)* |
| 0:25–0:45 | **Scenario** | Open `close-tieout-bank-cp` init workbook + mandate | "Bank statement staging: match truncated counterparty names from the bank narrative to the vendor master. When there's no match — leave it blank. Those rows go to review." |
| 0:45–1:25 | **Agent run** | `./demo/run_demo.sh` or `./demo/simulate_demo.sh close-tieout-bank-cp` | "tieout takes the workbook and mandate. Classify, execute, verify every answer cell." |
| 1:25–1:50 | **Exceptions** | `cat /tmp/syndicate-demo/exceptions.json` | "Two unmatched counterparties — preserved from real client data. Not silently overwritten." |
| 1:50–2:20 | **Human review** | `uv run python ../harness/exceptions.py review …` — approve one, reject one | "The accountant sees source-row evidence. Approve or reject before the workbook is final." |
| 2:20–2:40 | **Skill loop** | `./demo/run_skill_demo.sh` — highlight `close-tieout-le-map` | "Lookup patterns get a domain skill — no retraining." *(optional 10 sec)* |
| 2:40–3:00 | **AO** | AO dashboard, session count visible | "Syndicate pivot built with Agent Orchestrator." |
| 3:00–3:15 | **Close** | Logo / tagline | "tieout — every cell tied to its source. Validated on four hundred real spreadsheet tasks." |

**Secondary fixtures** (do not lead with): `close-tieout-le-map` (GL migration), `close-tieout-movements-rec` (pre-upload recon).

---

## Record these commands

```bash
# 0. Fixtures (once)
python3 demo/build_fixtures.py

# 1. Hero demo — offline (no Tinker; produces exceptions.json)
./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden

# 1b. Hero demo — live (optional; check Tinker credits first)
export TINKER_API_KEY= # set from .env
./demo/run_demo.sh close-tieout-bank-cp

# 2. Inspect outputs
cat /tmp/syndicate-demo/exceptions.json
cat /tmp/syndicate-demo/traces/close-tieout-bank-cp.jsonl | tail -3

# 3. Human review (interactive — record approve + reject)
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json

# 4. Skill loop (no inference)
./demo/run_skill_demo.sh

# 5. AO dashboard screenshot / screen recording (session count visible)
```

Step-by-step recording guide: `docs/VIDEO-RECORDING.md`

---

## What to show vs skip

| Show | Skip |
|------|------|
| `close-tieout-bank-cp` + 2 exceptions | Full 400-task eval |
| Exception evidence rows | Encode ablation / thinking-on |
| One approve + one reject in review CLI | LoRA / fine-tune story |
| AO dashboard + session count | Login, auth, Docker build |
| `./demo/run_skill_demo.sh` (10 sec) | All three fixtures in equal depth |

---

## AO sessions (log + show in video)

Update `docs/AO-SESSION-LOG.md` as sessions complete.

| # | Purpose | Status |
|---|---------|--------|
| 1 | Orchestrator: Syndicate task plan | done |
| 2 | Syndicate docs (this file, WORKFLOW, SYNDICATE) | done |
| 3 | Demo fixtures + `simulate_demo.sh` | done |
| 4 | Exception queue + pipeline hook | done |
| 5 | Skill demo + doc alignment | done |
| 6 | Demo video recording | in progress |

---

## Devpost checklist

- [ ] Track: **Autonomous Office of the CFO**
- [ ] Demo video (≤5 min) — bank-cp hero + AO dashboard
- [ ] GitHub repo link
- [ ] "How we used AO" — session count from `AO-SESSION-LOG.md`
- [ ] Hackathon pass posted, tag @aoagents

**Deadline:** Sept 6, 18:00 GMT-4 (23:00 GMT+1)

---

## Doc map (read order)

1. `docs/DOC-INDEX.md` — navigation hub  
2. `SYNDICATE.md` — submission summary  
3. **This file** — demo script  
4. `SYNDICATE-WORKFLOW.md` — CFO grounding + hero workflow  
5. `SYNDICATE-REQUIREMENTS.md` — judging weights, Devpost, credits  
6. `SYNDICATE-AO-INTEGRATION.md` — AO install + worker plan  
7. `demo/README.md` — fixture reference  
