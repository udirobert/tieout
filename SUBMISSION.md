# Submission: tieout

## Team

- Team name: tieout
- Members, one GitHub handle per line:
- Repo URL: https://github.com/udirobert/tieout

## What we built and why

TODO (150–300 words at venue): problem picked, what built, why that route, what worked / did not.
Be exact: model, prompt strategy, training data, tools the agent had.

## Models

TODO: exact model ids, or `tinker://<run-id>/sampler_weights/final` + base model with TTL cleared.
If fine-tuned: training data + how built, whether 400 goldens were in it, steps, LR, compute, wall time.

## Scores on the 400

```sh
uv run evaluate.py --predictions <your predictions.jsonl> --all --out results.json
```

```json
{"items": 400, "graded": 0, "missing": 0, "errors": 0, "pass_rate": 0, "cell_accuracy": 0, "pass_rate_cell_level": 0, "pass_rate_sheet_level": 0}
```

## Your run on the 400

- `predictions.jsonl`: path
- `outputs/`: path
- `traces/`: path
- `run.log`: path

## Code

Pipeline in `harness/`, runs in Docker reading `/data` writing `/out`. Env vars needed: TODO.

## Things to look at

- docs/CONSTRAINTS.md — space + credits + scoring params
- docs/SETUP.md — venue setup order
- docs/PLAN.md — team split
