# tieout — Syndicate submission

**Track:** Autonomous Office of the CFO  
**Devpost:** https://syndicate-by-maximor.devpost.com/  
**Repo:** https://github.com/udirobert/tieout

Every cell tied to its source.

---

## What it does

**tieout** automates spreadsheet reconciliation for finance close. Given a workbook and a
natural-language mandate, the agent executes the transform, verifies every answer cell,
routes exceptions to a human reviewer with source evidence, and archives a full audit trace.

Built for fund accountants and controllers — month-end tie-out, bank counterparty matching,
sub-ledger reconciliation, and multi-entity consolidation in Excel.

---

## Hero scenario (demo this)

**`close-tieout-bank-cp`** — bank statement staging: match truncated counterparty names from
bank narratives to a vendor master. When there is no match, the agent **leaves the cell blank**
and routes the row to the exception queue. Unmatched rows are preserved from real anonymised
fund-admin data — they are the product story, not a bug.

Full script: [`demo.md`](demo.md)

---

## Architecture

```
Workbook + mandate → Classify → Execute → Verify (≤3 retries) → Exception queue → Human review
                                      ↓
                            traces/ + exceptions.json
```

| Component | Role |
|-----------|------|
| `harness/pipeline.py` | Classify → values-first or codegen → verify → repair |
| `harness/exceptions.py` | Post-run queue + approve/reject CLI with evidence rows |
| `harness/skills.py` | Domain skill fragments (lookup, aggregation, consolidation) |
| `harness/verifier.py` | Blocks fatal errors; flags unresolved lookups |
| **Tinker** Qwen3.8-27B | Inference at demo time (`TINKER_API_KEY`) |
| **AO** | Built the Syndicate pivot (orchestrator + workers) — see below |

**Human judgment:** read-only source data, approve-gated writes, evidence-backed exceptions.
The accountant approves or rejects before unmatched rows are final.

---

## How we used AO

AO ([aoagents.dev](https://aoagents.dev/)) supervised **coding agents that built tieout** — not
the spreadsheet runtime at inference time.

| Phase | AO role |
|-------|---------|
| Orchestrator | Planned Syndicate work; spawned focused worker tasks |
| Workers | Exception queue, CFO demo fixtures, docs (isolated git worktrees) |
| Kanban | Session tracking — **total session count required in demo video** |

Install, session log, Devpost copy: [`submit.md`](submit.md)

---

## Demo video (what judges watch)

≤5 min · Must show **product workflow + AO dashboard with session count**

1. Hook — close still happens in Excel; one wrong cell fails tie-out
2. Bank counterparty workbook + mandate
3. `./demo/simulate_demo.sh close-tieout-bank-cp` → 2 exceptions
4. Human review CLI — approve one, reject one
5. Optional skill beat — `./demo/run_skill_demo.sh`
6. AO dashboard — scroll sessions, show count
7. Close — *every cell tied to its source*

---

## Try it

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Live inference (optional): set `TINKER_API_KEY` from `.env`, then `./demo/run_demo.sh close-tieout-bank-cp`

Env: `TINKER_API_KEY` (required for live), `GEMINI_API_KEY` (optional spare)

---

## Built with

AO · Python · openpyxl · Tinker (Qwen3.8-27B) · Neatlogs (traces)

**Team:** tieout · **Track:** Autonomous Office of the CFO
