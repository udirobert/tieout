# Documentation index — Syndicate submission

Single narrative: **bank counterparty match** (`close-tieout-bank-cp`) as hero demo;
exceptions + human review; built with AO.

---

## Read order (judges / you)

| # | File | Purpose |
|---|------|---------|
| 1 | [`SYNDICATE.md`](../SYNDICATE.md) | Submission summary — start here |
| 2 | [`SYNDICATE-DEMO.md`](SYNDICATE-DEMO.md) | 3-min video script + record commands |
| 3 | [`SYNDICATE-WORKFLOW.md`](SYNDICATE-WORKFLOW.md) | CFO pain + hero workflow detail |
| 4 | [`SYNDICATE-REQUIREMENTS.md`](SYNDICATE-REQUIREMENTS.md) | Devpost checklist, judging weights, credits |
| 5 | [`SYNDICATE-AO-INTEGRATION.md`](SYNDICATE-AO-INTEGRATION.md) | AO install + worker plan |
| 6 | [`demo/README.md`](../demo/README.md) | Fixture IDs + run commands |
| 7 | [`SESSION-STATUS.md`](SESSION-STATUS.md) | What's done vs pending |

---

## Supporting docs

| File | Purpose |
|------|---------|
| [`AO-SESSION-LOG.md`](AO-SESSION-LOG.md) | AO session IDs for Devpost + video |
| [`harness/README.md`](../harness/README.md) | Pipeline, exceptions CLI, eval vs demo path |
| [`TAXONOMY.md`](TAXONOMY.md) | Failure buckets → skills |
| [`SUBMISSION.md`](../SUBMISSION.md) | Encode hackathon archive (not the demo story) |
| [`HACKATHON-NOTES.md`](HACKATHON-NOTES.md) | Encode retro |

---

## Hero demo commands (canonical)

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
./demo/run_skill_demo.sh   # secondary beat — le-map
./demo/run_demo.sh close-tieout-bank-cp   # live Tinker (optional)
```

---

## Alignment rules

- **Demo story:** always lead with `close-tieout-bank-cp`, not movements-rec or le-map
- **Run commands:** use `python3 demo/...`, `./demo/simulate_demo.sh`, `cd research && uv run python ../harness/...`
- **Eval vs product:** 68% SpreadsheetBench is background validation in `SUBMISSION.md`, not the video hook
- **AO:** mandatory in video (dashboard + session count); log in `AO-SESSION-LOG.md`
