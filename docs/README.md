# Documentation — Syndicate submission

**Track:** Autonomous Office of the CFO · **Devpost:** https://syndicate-by-maximor.devpost.com/

Read in this order:

| # | Doc | For |
|---|-----|-----|
| 1 | [**SYNDICATE.md**](SYNDICATE.md) | What tieout is, how it works, how we used AO |
| 2 | [**demo.md**](demo.md) | Demo video script + commands (`close-tieout-bank-cp`) |
| 3 | [**submit.md**](submit.md) | Checklist, Devpost copy, AO install + session log |

Then the two deeper docs, each carrying its own measured caveats:

| Doc | For |
|-----|-----|
| [**COREWEAVE.md**](COREWEAVE.md) | The self-improvement loop and the governed correction memory — review workflow, what is and is not verified |
| [**NEO4J.md**](NEO4J.md) | Optional knowledge graph: cell lineage + counterparty retrieval, the measured read-path A/B, and the fixture's answer-key leak |

**Frontends** (both marimo, neither required for the CLI demo):

```bash
uv run --directory research marimo run ../demo/close_workspace.py   # governed memory review
uv run --directory research marimo run ../demo/loop_dashboard.py    # improvement curve + exception review
```

The knowledge graph has no UI of its own — it is read from the CLI
(`harness/graph.py query`) or from Cypher in the Aura console.

**Run the demo:**

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Code: [`demo/`](../demo/) · [`harness/`](../harness/)
