# Setup — venue order (space-safe)

Run in this order. Nothing here runs on the space-constrained Mac beforehand.

1. Team forms → declare research track → hand personal Google Cloud email to research desk.
   Tinker invite is manual. This is step 0, parallelize immediately.
2. Collect team API keys + model credits at desk. Put in `.env` (gitignored), never commit.
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

Excel formula note: newer functions need stored prefix or LibreOffice + Excel return #NAME?:
`_xlfn.XLOOKUP`, `_xlfn.UNIQUE`, `_xlfn.LET`, `_xlfn.CHOOSECOLS`, `_xlfn._xlws.FILTER`.
Classic SUM/SUMIFS/INDEX/MATCH/VLOOKUP need no prefix. Dates as real dates, not text.
Only graded cells (`answer_position` on `answer_sheet`) compared after recalc, normalized
(numbers 2dp, dates as serials, "" == empty). Everything else ignored.
