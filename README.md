# tieout

**Every cell tied to its source.**

Human-reviewed spreadsheet reconciliation for finance close. The new governed-memory
workflow turns an explicit correction into a scoped, replay-tested rule for future
suggestions. Keep the workbook process; stop solving the same exception from scratch.

**CoreWeave Hacks:** W&B/Weave experiments plus a local correction-memory prototype.
The original reconciliation engine is disclosed prior work from **Syndicate by Maximor** ·
Track 2: Autonomous Office of the CFO · [Devpost](https://syndicate-by-maximor.devpost.com/).

The new workflow is local and human-approved, not autonomous ledger posting or a
production multi-tenant service. See [the product, demo, and pilot plan](docs/COREWEAVE.md).

---

## close-keeper — Strands agent (Agents for Humans)

A [Strands Agents SDK](https://github.com/strands-agents/sdk-python) agent for the
financial close: it ties out workbooks in the background and **only surfaces when
there's a real decision to make**. New build on tieout's verified tools —
one recorded write path, governance-gated memory. See
[close_keeper/README.md](close_keeper/README.md).

Try it without an account:

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/udirobert/tieout/blob/main/close_keeper/demo_app.py)

```bash
uv sync --directory research --extra agent
research/.venv/bin/python -m close_keeper \
  "Tie out the close package (all tasks), then tell me which cells need my decision and why."
```

---

## Docs

| Read | Purpose |
|------|---------|
| [docs/NEO4J.md](docs/NEO4J.md) | Neo4j Aura: cell-lineage graph + lexical GraphRAG |
| [docs/COREWEAVE.md](docs/COREWEAVE.md) | CoreWeave Hacks: the self-improvement loop |
| [docs/SYNDICATE.md](docs/SYNDICATE.md) | Submission summary |
| [docs/demo.md](docs/demo.md) | Demo video script |
| [docs/submit.md](docs/submit.md) | Checklist + Devpost + AO |

---

## Governed close-memory demo (new)

```bash
uv sync --directory research
DEMO_DIR=$(mktemp -d /tmp/tieout-memory-demo.XXXXXX)
uv run --directory research python ../demo/memory_scenario.py --out-dir "$DEMO_DIR"
uv run --directory research marimo run ../demo/console.py   # Memory tab; picker finds $DEMO_DIR
```

Use the generated database/workbooks in the workspace. The script shows a
synthetic correction, replay gate, explicit activation, second-cycle suggestions,
and revocation. It ends revoked; `evidence.json` preserves every stage and
`cycle2-reviewed.xlsx` preserves the suggestions exported while active. No API
key is needed. This is a functional demonstration, not a measured customer ROI.

## Original reconciliation quick start

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Live: set `TINKER_API_KEY` from `.env`, then `./demo/run_demo.sh close-tieout-bank-cp`

## Self-improvement loop (CoreWeave Hacks)

Set `WANDB_API_KEY` in `.env` — enables W&B Inference + Weave tracing/evals.

```bash
# pipeline on W&B Inference, traced:
cd research && uv run python ../harness/pipeline.py \
  --dataset-dir ../demo/close-tieout --out-dir /tmp/tieout-wandb \
  --model wandb:meta-llama/Llama-3.3-70B-Instruct

# the loop: eval -> cluster failures -> mutate skills -> re-score -> keep/revert
uv run python loop.py --dataset-dir data/spreadsheetbench_verified_400 \
  --sample 20 --iters 3 --out-dir /tmp/tieout-loop

# console (marimo): Run tab = accuracy curve + exception review; Graph tab = lineage
uv run marimo run ../demo/console.py
```

## Qwen3-8B on SpreadsheetBench-400 (molab, free RTX Pro 6000)

Two eval passes against `Qwen/Qwen3-8B` via vLLM 0.29 — no API keys, served
locally on molab's free GPU. Headline finding: thinking-on is within a fraction
of a point of thinking-off on the sheet-level pass rate (13.48% partial vs
12.80% full), at ~10× the wall-clock cost and with several tasks blocked by
the model's 40k context ceiling. Both runs, predictions, results and a
side-by-side comparison live in `research/data/eval/qwen3-8b-molab/`.

## Knowledge graph (Neo4j)

Set `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` in `.env` (Aura) — every answer cell becomes a
stable `(:Cell)` node tied to its source cells, the counterparty it matched, and the exception it
raised, and the agent reads the seeded counterparty master (510 identities, against the 71-row copy
in the workbook) back to ground column K. Without creds it no-ops: identical `exceptions.json`,
prompts, and scores. For lineage the graph is a derived index, not the authority — `rebuild_graph.py`
reconstructs it from a run's artifacts, so a paused or deleted free Aura instance costs nothing.
Details, including the measured read-path A/B and the fixture's answer-key leak, in
[docs/NEO4J.md](docs/NEO4J.md).

```bash
# seed the counterparty master, then write lineage offline (no API key)
cd research && uv run --extra graph python ../demo/seed_graph.py
TIEOUT_RUN_ID=demo ./demo/simulate_demo.sh close-tieout-bank-cp

# read candidates back (the GraphRAG retrieval), or run live with the read on
cd research && uv run --extra graph python ../harness/graph.py query "NIP LIT"
TIEOUT_GRAPHRAG=1 ./demo/run_demo.sh close-tieout-bank-cp

# recover the graph from artifacts after an Aura pause/delete
cd research && uv run --extra graph python ../demo/rebuild_graph.py /tmp/syndicate-demo
```

## Example output

Bank counterparty match: `Matched Sender/Beneficiary` filled where the lookup resolves; empty cells are routed to `exceptions.json` with source-row evidence.

![tieout output screenshot](docs/assets/output-screenshot.png)

---

## Layout

```
close_keeper/  Strands agent for the close (Agents for Humans)
demo/          CFO fixtures + scripts + marimo console
docs/          SYNDICATE.md, demo.md, submit.md
harness/       agent pipeline
research/      dependencies (uv sync)
```

Built with AO · Python · openpyxl · Tinker (Qwen3.8-27B)
