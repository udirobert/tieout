# tieout — Every cell tied to its source.

Research-track entry for Ylookup x Encode AI Hackathon (5–6 Sept 2026, Encode Hub).
Task: SpreadsheetBench Verified, 400 tasks. Given workbook + instruction, return workbook with answer cells filled.

**Demo video:** [tweet with walkthrough](https://x.com/UNgethe/status/2096550517878989285) · **Write-up:** [Nine Points, Then We Trained](https://medium.com/@ungethe/nine-points-then-we-trained-0bb2784446fc) (Medium)

## Scores (SpreadsheetBench Verified 400)

| Run | pass_rate | cell_accuracy | Where |
|-----|-----------|---------------|-------|
| **Ship (clone-run)** | **68.00%** (272/400) | **37.09%** | `research/data/eval/clone_run/` |
| Container reproduction | 67.75% (271/400) | 37.00% | `research/data/eval/container400/` |

Ship artifacts: `predictions.jsonl`, `results.json`, `run.log`, `traces/` (400 tasks). Full write-up and ablation table in `SUBMISSION.md`.

Upstream starter lives untouched in `research/` (from https://github.com/ylookup/encode-hackathon).
All team code lives outside `research/`. Hacking started Sat 12:00 — this repo carries
everything from that point (skeletons + docs committed at hack start, all implementation since).

## Layout

```
tieout/
  research/            UPSTREAM, read-only reference (sb.py, evaluate.py, baseline/)
  harness/             our pipeline: classify -> codegen/values -> exec -> verify -> retry
  docs/                TEAM-BRIEF.md (current), SESSION-STATUS.md, CONSTRAINTS.md, SETUP.md
  Dockerfile           submission container (/data ro -> /out)
  SUBMISSION.md        150–300 word write-up + scores (from research/SUBMISSION_TEMPLATE.md)
  research/data/eval/clone_run/   ship evidence: predictions.jsonl, results.json, run.log, traces/
```

## Design principles

- Tinker Qwen3.8-27B default; thinking off; 16k output tokens; temperature 0
- Sheet-level: model writes openpyxl → sandbox exec → read back → repair
- Cell-level: values-first JSON write + repair; codegen as fallback
- Never blank: always write a line + an xlsx (init copy on total failure)
- Current plan: `docs/TEAM-BRIEF.md`. Do not follow `docs/PLAN.md` / `docs/PATTERNS.md`.

## Venue-first rule

This Mac is space-constrained. No `uv sync`, no dataset download, no LibreOffice,
no `docker build`, no local weights until the venue. See `docs/CONSTRAINTS.md`.
