# Demo fixtures — Syndicate (Track 2: Office of the CFO)

Finance-framed scenarios extracted from **Ylookup anonymised datasets** (~44 KB in repo).
Source files stay in `~/Downloads/Ylookup Hackathon Datasets` — not copied wholesale.

**Hero scenario for Syndicate video:** `close-tieout-bank-cp` (bank counterparty match → exception queue).

## Build

```bash
python3 demo/build_fixtures.py
# or: YLOOKUP_DATASETS=/path/to/datasets python3 demo/build_fixtures.py
```

## Scenarios (built)

| ID | CFO workflow | Source | Demo role |
|----|--------------|--------|-----------|
| **`close-tieout-bank-cp`** | **Bank counterparty match → exception queue** | Dataset 01 `Staging Sheet` | **Hero — record this** |
| `close-tieout-le-map` | Entity mapping (fund-admin GL migration) | Dataset 02 `LE Mapping` | Skill demo beat |
| `close-tieout-movements-rec` | Pre-upload reconciliation (OK / EXCEPTION) | Dataset 02 `Movements Rec` | Secondary |

## Run

```bash
# Offline — exception queue (no Tinker, good for video)
./demo/simulate_demo.sh close-tieout-bank-cp
./demo/simulate_demo.sh close-tieout-movements-rec /tmp/syndicate-demo golden

# Skill improvement loop (no inference)
./demo/run_skill_demo.sh

# Live agent (requires TINKER_API_KEY — see SYNDICATE-REQUIREMENTS.md)
export TINKER_API_KEY= # set from .env
./demo/run_demo.sh close-tieout-bank-cp

# Human review after run
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

## Layout

```
demo/close-tieout/
  dataset.json
  spreadsheet/<id>/
    1_<id>_init.xlsx
    1_<id>_golden.xlsx    # for local eval only — harness must not read during run
    prompt.txt
```

## Human review loop

Rows that fail verification or have blank matches (by design in source data) are written to
`exceptions.json` after each run. Review via CLI — see `docs/SYNDICATE-WORKFLOW.md` and
`docs/SYNDICATE-DEMO.md`.

## Status

| Scenario | Built | Demo role |
|----------|-------|-----------|
| close-tieout-bank-cp | yes | **hero** |
| close-tieout-le-map | yes | skill beat |
| close-tieout-movements-rec | yes | secondary |

Rebuild after editing source datasets: `python3 demo/build_fixtures.py`
