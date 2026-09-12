# tieout

**Every cell tied to its source.**

Autonomous spreadsheet reconciliation for finance close — verify every answer cell,
route exceptions to human review, archive an audit trace.

**Syndicate by Maximor** · Track 2: Autonomous Office of the CFO · [Devpost](https://syndicate-by-maximor.devpost.com/)

---

## Docs

| Read | Purpose |
|------|---------|
| [docs/COREWEAVE.md](docs/COREWEAVE.md) | CoreWeave Hacks: the self-improvement loop |
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

# dashboard (marimo): accuracy curve + exception review
uv run marimo run ../demo/loop_dashboard.py
```

## Example output

Bank counterparty match: `Matched Sender/Beneficiary` filled where the lookup resolves; empty cells are routed to `exceptions.json` with source-row evidence.

![tieout output screenshot](docs/assets/output-screenshot.png)

---

## Layout

```
docs/       SYNDICATE.md, demo.md, submit.md
demo/       CFO fixtures + scripts
harness/    agent pipeline
research/   dependencies (uv sync)
```

Built with AO · Python · openpyxl · Tinker (Qwen3.8-27B)
