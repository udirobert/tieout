# tieout

**Every cell tied to its source.**

Autonomous spreadsheet reconciliation for finance close — verify every answer cell,
route exceptions to human review, archive an audit trace.

**Syndicate by Maximor** · Track 2: Autonomous Office of the CFO · [Devpost](https://syndicate-by-maximor.devpost.com/)

---

## Docs

| Read | Purpose |
|------|---------|
| [docs/SYNDICATE.md](docs/SYNDICATE.md) | Submission summary |
| [docs/demo.md](docs/demo.md) | Demo video script |
| [docs/submit.md](docs/submit.md) | Checklist + Devpost + AO |

---

## Quick start

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Live: set `TINKER_API_KEY` from `.env`, then `./demo/run_demo.sh close-tieout-bank-cp`

---

## Layout

```
docs/       SYNDICATE.md, demo.md, submit.md
demo/       CFO fixtures + scripts
harness/    agent pipeline
research/   dependencies (uv sync)
```

Built with AO · Python · openpyxl · Tinker (Qwen3.8-27B)
