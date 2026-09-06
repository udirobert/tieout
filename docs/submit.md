# Submit — checklist, Devpost, AO

**Deadline:** Sunday 6 September 2026, **23:00 GMT+1**  
**Devpost:** https://syndicate-by-maximor.devpost.com/ · **Discord:** https://discord.gg/Sy3EwRBQX3

---

## Status

| Item | Status |
|------|--------|
| Submission doc | done — [SYNDICATE.md](SYNDICATE.md) |
| Demo script | done — [demo.md](demo.md) |
| Demo fixtures + exception queue | done |
| AO desktop + sessions logged | done — 5 AO sessions used (see session log) |
| Demo video | done — https://youtu.be/lmOKmOSSbYo |
| Devpost | pending |

**Next:** Fill Devpost using the draft below → submit.

---

## Judging checklist

| Criterion | Weight | Evidence |
|-----------|--------|----------|
| AO usage & build process | 25% | AO dashboard + session count in video; session log below |
| Technical execution | 25% | Verify + retry; never-blank; traces; exception queue |
| Track fit & value | 25% | Real fund-admin data; bank counterparty hero demo |
| Demo & usability | 15% | [demo.md](demo.md), `./demo/simulate_demo.sh` |
| Innovation | 10% | Skills-from-failure loop without retraining |

**Must submit:**
- [ ] Track: Autonomous Office of the CFO
- [ ] Public repo + demo video (3–5 min)
- [ ] Video shows AO dashboard + **total session count**
- [ ] All team members registered on Devpost
- [ ] Hackathon pass posted (X/LinkedIn, tag @aoagents)

---

## AO

AO supervises coding agents building the repo. Tinker runs the spreadsheet agent at demo time.

**Install:** [agent-orchestrator DMG](https://github.com/Untrivial-ai/agent-orchestrator/releases/latest/download/agent-orchestrator-darwin-arm64.dmg) → open Agent Orchestrator → add project `/Users/udingethe/Dev/tieout`

```bash
ao doctor && ao status && ao session ls   # session count for video
```

**What judges need in the video:** AO dashboard visible, session list scrolled, total count readable for ≥5 seconds.

### Session log

Fill before Devpost. Count must match the video.

| Session ID | Role | Task | Status |
|------------|------|------|--------|
| tieout-9 | orchestrator | Syndicate plan + worker spawn | done |
| tieout-10 | worker | Exception queue + pipeline | done |
| tieout-11 | worker | Demo fixtures + scripts | done |
| tieout-8 | worker | Docs + Devpost | done |
| tieout-12 | worker | Demo video script | done |

**Total sessions:** 5

### Devpost — How we used AO

> We used Agent Orchestrator as the development control plane for tieout. One orchestrator
> session broke work into focused tasks; **4 worker sessions** implemented the exception queue,
> Ylookup CFO demo fixtures, submission docs, and demo video script in isolated git worktrees.
> The spreadsheet agent runs via Tinker at inference time; AO orchestrated the engineering.
> The demo video shows the AO dashboard with the total session count of **5**.

---

## Devpost draft

### Project name

tieout

### Tagline

Every cell tied to its source — autonomous spreadsheet reconciliation for finance close.

### Track

Autonomous Office of the CFO

### What does your project do?

Private markets and corporate finance teams still close books in Excel. Month-end tie-out,
bank counterparty matching, and multi-entity consolidation are repetitive and error-prone.

tieout takes a workbook + plain-English mandate, executes the transform, verifies every answer
cell, retries with attribution-guided repair, and routes unmatched rows to a human-review
exception queue with source evidence. Full audit trail via `traces/` and `exceptions.json`.

### How we used AO

> We used Agent Orchestrator as the development control plane for tieout. One orchestrator
> session broke work into focused tasks; 4 worker sessions implemented the exception queue,
> Ylookup CFO demo fixtures, submission docs, and demo video script in isolated git worktrees.
> The spreadsheet agent runs via Tinker at inference time; AO orchestrated the engineering.
> The demo video shows the AO dashboard with the total session count of 5.

### How does it work?

- Pipeline: `harness/pipeline.py` — classify → execute → verify → retry → exceptions
- Exception queue: `harness/exceptions.py` — evidence rows + approve/reject CLI
- Model: Tinker Qwen/Qwen3.8-27B
- Demo: `demo/close-tieout/` — anonymised fund-admin CFO scenarios

### Demo video URL

https://youtu.be/lmOKmOSSbYo

### GitHub

https://github.com/udirobert/tieout

### Try it

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

### Results

- Hero demo: bank counterparty match with 2 preserved exceptions + human review workflow
- Never-blank contract: every run emits workbook + trace + exception file when applicable

### Team

__Names__

### Social

- Discord showcase: posted in #showcase (or #submissions)
- X/LinkedIn pass tagging @aoagents: https://x.com/UNgethe/status/2096714226509209934?s=20

#### Discord showcase draft

```text
🧾 tieout — every cell tied to its source.

Track: Autonomous Office of the CFO (#SyndicateByMaximor)

Problem: Finance teams still close the books in spreadsheets. Bank counterparty matching, legal-entity mapping, and movements reconciliation are manual and error-prone — one wrong cell breaks the close.

What it does: tieout takes a workbook + plain-English mandate, executes the transform, verifies every answer cell, retries with attribution, and routes unmatched rows to a human-review exception queue with source evidence.

Built with Agent Orchestrator: 5 Devin sessions (orchestrator + 4 workers) handled exception queue, demo fixtures, docs/Devpost, and this video script.

🔗 GitHub: https://github.com/udirobert/tieout
🎥 Demo: https://youtu.be/lmOKmOSSbYo

Would love feedback and questions!
```

---

## Pre-submit

1. [x] `./demo/simulate_demo.sh close-tieout-bank-cp` — exceptions OK
2. [x] Demo video uploaded (AO dashboard visible)
3. [x] Devpost submitted
4. [x] Social posted

**Tinker (optional live run):** check credits before `./demo/run_demo.sh close-tieout-bank-cp`
