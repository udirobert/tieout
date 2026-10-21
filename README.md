# tieout

**Every cell tied to its source.**

Human-reviewed spreadsheet reconciliation for finance close. An explicit correction
becomes a scoped, replay-tested rule for future suggestions — keep the workbook
process, stop solving the same exception from scratch.

**CoreWeave Hacks:** W&B/Weave experiments plus a local correction-memory prototype.
The original reconciliation engine is disclosed prior work from **Syndicate by
Maximor** · Track 2: Autonomous Office of the CFO · [Devpost](https://syndicate-by-maximor.devpost.com/).

The new workflow is local and human-approved — not autonomous ledger posting, not a
production multi-tenant service. See [docs/COREWEAVE.md](docs/COREWEAVE.md).

---

## Frontends

Three surfaces, all readable without a key:

| Frontend | Where | What it is |
|---|---|---|
| **Public site** | [udirobert.github.io/tieout](https://udirobert.github.io/tieout/) — source [docs/index.html](docs/index.html) | The workflow, the counted numbers, the film, and **Fig. 01** — the close ledger, an isometric close package where only the cells needing a human are lit. |
| **Tie-out console** | [demo/console.py](demo/console.py) — [open in molab](https://molab.marimo.io/github/udirobert/tieout/blob/main/demo/console.py) | The marimo instrument over **Run / Memory / Graph**: run grading and exception review, governed memory, lineage graph. |
| **Close desk** | [close_keeper/app.py](close_keeper/app.py) | The customer-facing surface: load a close package → the queue with its evidence → decide → the memory → the history. |

```bash
# the console and the close desk, locally
uv sync --directory research
uv run --directory research marimo run ../demo/console.py
uv run --directory research marimo run ../close_keeper/app.py
```

All three read the same artifacts and write through the same
`exceptions.apply_decisions`. None of them has a third way to change a
workbook, and every decision is appended to the tenant's ledger before anything
is touched.

---

## What is behind it

| | |
|---|---|
| **One evidence model** | `harness/evidence.py` — the cell, its current value, the proposed value, the reason, and the source rows. The CLI, the console, the walkthrough and the ledger all render *this*, so the surfaces cannot drift. |
| **Tenant isolation** | `harness/tenant.py`, `harness/tenant_store.py` — a store belongs to one tenant; another tenant's rows are structurally invisible, not merely filtered. |
| **An append-only ledger** | `harness/ledger.py` — what a human decided, when, and on what evidence. It outlives the workbook it describes. |
| **Measured closes** | `harness/close_metrics.py` — exceptions raised, decisions, minutes in queue, reopened exceptions. Computed from what those two stores already hold. |
| **Governed memory** | `harness/memory_store.py` — correction → propose → validate → activate → revoke, enforced in the tools, not in a prompt. |

Details in [docs/README.md](docs/README.md) and [docs/COREWEAVE.md](docs/COREWEAVE.md).

## close-keeper — Seapoint MCP + Claude (FinOps Hackathon 2026)

**FinOps Hackathon · Seapoint × 13books Capital · Claude · October 2026.**
close-keeper connects to Seapoint's MCP — live transactions, invoices, burn/cash/runway
— runs the tie-out in the background, and **only surfaces the judgment queue: the
fraction it won't code without a human, each with its evidence.**

Built with Claude (Anthropic API) and the
[Strands Agents SDK](https://github.com/strands-agents/sdk-python) on top of tieout's
verified machinery. Seapoint's mutating tools are held behind one governed, evidenced,
logged write path.

**Outcome: did not place.** The judges' reason was that the entry didn't show a workflow
people already do and how the agent improves on it — fair, and now written out under
[The workflow this sits inside](close_keeper/README.md#the-workflow-this-sits-inside).
The technical claims are unchanged and itemised under
[Verified](close_keeper/README.md#verified).

Try it without an account (local close package, no keys, no Seapoint):

[![Open in molab](https://marimo.io/molab-shield.svg)](https://molab.marimo.io/github/udirobert/tieout/blob/main/close_keeper/demo_app.py)

```bash
uv sync --directory research --extra agent
research/.venv/bin/python -m close_keeper --no-seapoint \
  "Tie out the close package (all tasks), then tell me which cells need my decision and why."
```

For live Seapoint, the MCP is connected through Claude (the sandbox admits only
Claude's connector) and the beats are driven in that session. Full detail:
[close_keeper/README.md](close_keeper/README.md).

---

## Docs

**[docs/README.md](docs/README.md) is the hub** — read it to find the right page.

| Read | Purpose |
|------|---------|
| [docs/README.md](docs/README.md) | Documentation hub: frontends, what to read, commands |
| [docs/SYNDICATE.md](docs/SYNDICATE.md) | What tieout is, how it works, how we used AO |
| [docs/COREWEAVE.md](docs/COREWEAVE.md) | The governed correction memory and the self-improvement loop — review workflow, what is and is not verified |
| [docs/NEO4J.md](docs/NEO4J.md) | Optional knowledge graph: cell lineage + counterparty retrieval, the measured read-path A/B, and the fixture's answer-key leak |
| [docs/demo.md](docs/demo.md) | Demo video script + commands (`close-tieout-bank-cp`) |
| [docs/submit.md](docs/submit.md) | Checklist, Devpost copy, AO install + session log |
| [docs/HACKATHONS.md](docs/HACKATHONS.md) | close-keeper's next entries: which events admit an existing project, and what each needs |
| [close_keeper/README.md](close_keeper/README.md) | The active surface: the agent, the governed write path, the Seapoint MCP |
| [demo/README.md](demo/README.md) | Fixtures, scenarios, and the demo commands |
| [research/README.md](research/README.md) | The research track (SpreadsheetBench) and how to score it |
| [videos/close-keeper-finops/](videos/close-keeper-finops/) | The 2:00 entry film, its frame-by-frame source, and `BRIEF.md` |
**Measured result:** on SpreadsheetBench-400 with Qwen3-8B served locally, thinking-on
beats thinking-off by ~5 points on sheet-level pass rate and ~18 points on cell-level
pass rate, at 4× the wall-clock. Write-up and artifacts:
[research/data/eval/qwen3-8b-molab/](research/data/eval/qwen3-8b-molab/).

---

## Quick start

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Unmatched cells are routed to `exceptions.json` with source-row evidence — empty is an
answer. Live inference (optional): set `TINKER_API_KEY` in `.env`, then
`./demo/run_demo.sh close-tieout-bank-cp`.

More commands — governed memory demo, self-improvement loop, Neo4j — in
[docs/README.md](docs/README.md).

---

## Layout

```
close_keeper/  Strands agent for the close (Agents for Humans)
demo/          CFO fixtures + scripts + marimo console
docs/          the documentation hub and its pages
harness/       agent pipeline
research/      dependencies (uv sync)
```

Built with AO · Python · openpyxl · marimo · Tinker (Qwen3.8-27B)
