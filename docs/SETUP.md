# Setup — venue order (space-safe)

Run in this order. Nothing here runs on the space-constrained Mac beforehand.

1. Team forms → declare research track → hand personal Google Cloud email to research desk.
   Tinker invite is manual. This is step 0, parallelize immediately.
2. Collect team API keys + model credits at desk. Put in `.env` (gitignored), never commit.
   Keys in play: `TINKER_API_KEY` (fine-tune + sampling), `GEMINI_API_KEY` (AI Studio on the
   gcplab account — free, primary inference). OpenRouter skipped (unfunded).
   Sync `.env` to the VM manually (gitignored, not transported by git):
   `gcloud compute scp .env tieout-builder:~/tieout/research/.env`
3. Venue wifi:
   ```
   cd research
   uv sync
   uv run data/download.py
   ```
4. LibreOffice for scorer recalc (needed for formula tasks):
   macOS `brew install --cask libreoffice`, Linux `sudo apt install libreoffice-calc`.
   If `soffice` elsewhere: `SOFFICE=/path/to/soffice`. Always run via `uv run`.
   Iterate first with `--no-recalc` to avoid needing it.
5. Smoke test (subset, cheap):
   ```
   uv run baseline/llm_predict.py --out-dir submissions/my-llm --model <qwen-id> --ids 13-1,51-12
   uv run evaluate.py --predictions submissions/my-llm/predictions.jsonl --no-recalc
   uv run evaluate.py --oracle   # must be 1.0
   ```
6. Build container early Sat afternoon, test unattended start:
   ```
   docker build -t tieout .
   docker run --rm -e OPENROUTER_API_KEY -e TINKER_API_KEY -v <dataset>:/data:ro -v <empty>:/out tieout
   ```
7. Full 400 run + `evaluate.py --all --out results.json` before Sun 12:00. Paste summary into SUBMISSION.md.

## VM (done Sat ~12:45, Mac stays lightweight)

GCP project `priv-mkt-hack26lon-3727`, VM `tieout-builder` (europe-west2-a, e2-standard-4,
Ubuntu 24.04, 50GB): LibreOffice 24.2 + Docker 29 + uv installed, repo cloned at `~/tieout`,
dataset verified, `evaluate.py --oracle` = 1.0 **with full recalc**. Access via
`gcloud compute ssh tieout-builder --zone=europe-west2-a`. Division of labor: Mac = edit/commit/push
+ subset iteration with `--no-recalc`; VM = scored runs, container build + unattended test.
Heavy work is VM-only — do not install LibreOffice/Docker on the Mac.

Excel formula note: newer functions need stored prefix or LibreOffice + Excel return #NAME?:
`_xlfn.XLOOKUP`, `_xlfn.UNIQUE`, `_xlfn.LET`, `_xlfn.CHOOSECOLS`, `_xlfn._xlws.FILTER`.
Classic SUM/SUMIFS/INDEX/MATCH/VLOOKUP need no prefix. Dates as real dates, not text.
Only graded cells (`answer_position` on `answer_sheet`) compared after recalc, normalized
(numbers 2dp, dates as serials, "" == empty). Everything else ignored.
