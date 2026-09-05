# Results checklist — run at venue, paste into SUBMISSION.md

## A. Run log (every run: model, n, temp, out-dir — the ablation table writes itself)

| run | date | model | n | temp | path | skills | out-dir | pass_rate | cell_acc |
|---|---|---|---|---|---|---|---|---|---|
| tinker-400 baseline (no repair) | 2026-09-05 | tinker:Qwen/Qwen3.8-27B | 400 | 0 (default) | values-first | off | /tmp/tinker-400 | 0.4675 | 0.3728 |
| sheet20 codegen probe | 2026-09-05 | tinker:Qwen/Qwen3.8-27B | 20 (sheet fails) | ? | auto/codegen | off | /tmp/sheet20-codegen | 0.55 (on subset) | 0.9911 |

Baseline scoring: official `results.json` summary (recalc?) + local `--no-recalc` confirm below.
- [x] `--no-recalc` confirm on /tmp/tinker-400 (2026-09-05):
      `research/.venv/bin/python evaluate.py --predictions /tmp/tinker-400/predictions.jsonl --no-recalc`
      → items 400, graded 400, missing 0, errors 0,
      **pass_rate 0.4675, cell_accuracy 0.3728** (cell 0.48 / sheet 0.44).
      Matches official results.json exactly. Harness: 373 ok / 14 partial / 13 error.

## B. Write-up skeleton (SUBMISSION.md structure)

1. **Result** — headline pass_rate (+ cell_accuracy tie-break), items=400, one paragraph.
2. **Method** — values-first + codegen with execution feedback (repair loop); skills
   library (`skills/library.py`, generic fragments retrieved by category); serializer
   incl. merged cells / fill; container contract respected (/data ro → /out).
3. **Ablations** — table from §A: baseline vs +codegen vs +skills vs +repair
   (published anchor: execution feedback ≈2.5x, SpreadsheetBench Table 2; WML 74.67).
4. **Failure taxonomy** — from §C traces; what we fixed vs what remains.
5. **Protocol** — fixed ordering, temp, seeds; mean±std where repeatable.
6. **Env** — env-var NAMES only (no keys ever).

## Ablation plan (skills retrieval-by-category)

- Matrix: {values, codegen} × {skill off, skill on} on a fixed 40-task stratified
  subset (10 per category: lookup / aggregation / date / sheet-reorg), then full-400
  if Δ ≥ 2pts.
- Retrieval: keyword rules over instruction text only (`library.categorize`), max 2
  fragments, serialization guard always on. No task-ids, no dataset-specific strings
  (held-out private fund set punishes overfit).

```sh
# subset iterate (no recalc, no LibreOffice needed)
uv run evaluate.py --predictions <out>/predictions.jsonl --no-recalc

# oracle must be 1.0
uv run evaluate.py --oracle

# official self-score (requires LibreOffice / SOFFICE for formula recalc)
uv run evaluate.py --predictions <out>/predictions.jsonl --all --out results.json
```

`results.json` summary block goes into SUBMISSION.md. `items` must be 400.
Reported scores decide run order only — judges' run ranks.

## Baseline Run (Qwen3.8-27B, Values-First v0, no repair, 2026-09-05)

```json
{
  "items": 400,
  "graded": 400,
  "missing": 0,
  "errors": 0,
  "pass_rate": 0.4675,
  "cell_accuracy": 0.3728,
  "pass_rate_cell_level": 0.48,
  "pass_rate_sheet_level": 0.44
}
```

Pre-submit gates:
- [x] predictions.jsonl has 400 lines, every `outputs/<id>.xlsx` exists + readable (/tmp/tinker-400)
- [x] traces/<id>.jsonl one line per model call, failures kept with `error`, no golden values in prompts
- [x] run.log is raw stdout/stderr, unedited
- [ ] Dockerfile builds + starts unattended: `docker run --rm -e <KEYS> -v <dataset>:/data:ro -v <empty>:/out tieout`
- [ ] No API keys in repo. Env names listed in SUBMISSION.md.
- [x] `items: 400` in results.json summary (400 graded, 0 missing, 0 errors)
