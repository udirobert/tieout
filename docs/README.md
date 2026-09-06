# Documentation — Syndicate submission

**Track:** Autonomous Office of the CFO · **Devpost:** https://syndicate-by-maximor.devpost.com/

Read in this order:

| # | Doc | For |
|---|-----|-----|
| 1 | [**SYNDICATE.md**](SYNDICATE.md) | What tieout is, how it works, how we used AO |
| 2 | [**demo.md**](demo.md) | Demo video script + commands (`close-tieout-bank-cp`) |
| 3 | [**submit.md**](submit.md) | Checklist, Devpost copy, AO install + session log |

**Run the demo:**

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Code: [`demo/`](../demo/) · [`harness/`](../harness/)
