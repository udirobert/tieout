# tieout — Every cell tied to its source.

Research-track entry for Ylookup x Encode AI Hackathon (5–6 Sept 2026, Encode Hub).
Task: SpreadsheetBench Verified, 400 tasks. Given workbook + instruction, return workbook with answer cells filled.

Upstream starter lives untouched in `research/` (from https://github.com/ylookup/encode-hackathon).
All team code lives outside `research/`. Hacking started Sat 12:00 — this repo carries
everything from that point (skeletons + docs committed at hack start, all implementation since).

## Layout

```
tieout/
  research/            UPSTREAM, read-only reference (sb.py, evaluate.py, baseline/)
  harness/             our pipeline: classify -> write py -> exec -> verify -> retry
  docs/                CONSTRAINTS.md, SETUP.md, PLAN.md (this machine is space-constrained)
  Dockerfile           submission container (/data ro -> /out)
  SUBMISSION.md        150–300 word write-up + scores (from research/SUBMISSION_TEMPLATE.md)
  predictions.jsonl    our run on the 400 (generated at venue, not now)
  outputs/ traces/ run.log results.json   generated at venue
```

## Design principles (distilled from prior builds)

- Task-typed prompts + time-guard + offline container discipline
- Model writes code + executes + iterates, SUMMARY_JSON, positive control
- Deterministic openpyxl surgery, seeded + header-tolerant
- Deterministic rules decide, model narrates + receipt
- Preview → atomic-commit import flow (product demo only)

## Venue-first rule

This Mac is space-constrained. No `uv sync`, no dataset download, no LibreOffice,
no `docker build`, no local weights until the venue. See `docs/CONSTRAINTS.md`.
