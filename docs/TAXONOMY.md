# Failure taxonomy — /tmp/tinker-400 (400 tasks, Qwen3.8-27B, no-repair baseline, 2026-09-05)

> **Syndicate:** Maps to CFO workflow categories in `docs/SYNDICATE-WORKFLOW.md` and skill
> fragments in `harness/skills.py`. Used for failure clustering and skill injection demos.

Headline: **pass_rate 0.4675, cell_accuracy 0.3728** (cell 132/275 = 48.0%, sheet 55/125 = 44.0%).
Harness status 373 ok / 14 partial / 13 error. Attempts/task mean 1.15, max 3.

| failure bucket | cell (n=275) | sheet (n=125) | all 400 |
|---|---|---|---|
| PASS | 132 (48.0%) | 55 (44.0%) | 187 (46.8%) |
| reasoning (graded wrong values) | 136 (49.5%) | 52 (41.6%) | 188 (47.0%) |
| serialization (missing answer cells) | 5 (1.8%) | 8 (6.4%) | 13 (3.3%) |
| parse/truncation (JSONDecodeError, 12k–34k char replies) | 0 | 8 (6.4%) | 8 (2.0%) |
| other error | 2 (0.7%) | 2 (1.6%) | 4 (1.0%) |

Key reads:
- **Reasoning dominates**: 188/213 failures (88%) are "ran fine, wrong values" — the biggest
  lever remains model quality / execution-feedback repair, not plumbing.
- **Serialization** = missing answer cells (14 partial + worse in error status): long answer
  ranges dropped mid-list. A's range-expansion fix (task_0010 era) targets this.
- **Parse/truncation** is sheet-only (8 tasks, JSON replies >12k chars hit JSONDecodeError).
  Codegen path or chunked output would bypass; raise max_tokens per methodology §1.
- **Retry recovery is weak**: 31 tasks retried (2×2, 29×3 attempts) → only 4 recovered to
  pass (13%). Blind resampling is the documented weak baseline — confirms attribution-guided
  repair (methodology §4.2). 27/31 retried tasks still failed.
- Output tokens max 16384 (cap hit), latency mean 35.6s / p50 6.6s / max 307s.

---

# Taxonomy probe — 20-task sample (10 cell + 10 sheet), principles only

Source: 400-task dataset stats + sampled `instruction`/`prompt.txt` (no workbooks opened).
Full probe data lives in `/tmp/tieout-scratch` (outside the repo, deleted after venue).

## Dataset shape

- 275 cell-level / 125 sheet-level. `answer_position` is a range on `answer_sheet`
  (single range, cross-sheet `'Test'!G3:G58`, or multi-sheet lists).
- Instruction length: min 38 / median 475 / max 2176 chars. Prompts are raw forum posts:
  rambling, partial formulas quoted, "tried X for 3 hours" context.
- Keyword hits over 400: formula 208, match 89, format 81, macro 55, vba 50,
  index 34, sort 21, duplicate 19, filter 18, sumif 13, vlookup 12, xlookup 2, pivot 2.

## Cell-level buckets (sampled)

1. **Lookup repair** (VLOOKUP/INDEX-MATCH/OFFSET): conditional return ("if E==D return time
   from M"), days-since-last-sale with ascending dates, every-nth-row via OFFSET,
   COUNTBLANK pattern shifted by 3 cols. Strategy: compute VALUES in Python, don't
   parrot the broken formula.
2. **Multi-criteria aggregation**: heat-map COUNTIFS on name + time-of-day window
   (21:30–22:00 ignoring date), bond cashflow matrix E6:AB25 (freq 1/2/4 + maturity).
   Strategy: datetime parse + vectorized loops; watch time-only comparisons.
3. **Conditional copy without VBA**: Input→Output where To-Do=yes, skip empties.
   Strategy: filter-then-compact in Python.
4. **Formatting traps**: one task mixes "Arial/bold/#CCCCCC fill" with a real formula ask.
   Grading ignores formatting — write values, ignore style demands (except yellow-highlight
   gating below, which IS logic).

## Sheet-level buckets (sampled)

1. **VBA row delete/filter** (majority): delete where col-B first char not H/A, filter
   groups (@9T/SAL/T9A) over 13k rows, delete where col-C is not #N/A, trim rows above
   first 'Invoice No.'. Strategy: implement the EQUIVALENT Python transform (never run VBA);
   delete bottom-up, preserve row 1 / formatting. Perf matters on 10k+ rows.
2. **Merge/dedupe/consolidate**: dict+array merge on cols A+B+C summed from G; multi-sheet
   net (Existing + Additions − Retired) into Consolidated Tracker. Strategy: hash keys,
   set arithmetic on row tuples.
3. **Cross-sheet reshape**: header-exists → insert N rows → append + copy into Output sheet.
   Strategy: sheet-aware openpyxl surgery, keep sheet names exact (quotes/spaces matter).
4. **Formatting-dependent logic** (hardest): "apply formula only for yellow-highlighted rows",
   concatenation with prefix `//[`. Requires reading `cell.fill` — plain serialization drops it.
   Serializer MUST include fill color for these tasks.
5. **Single-cell VBA compute**: 10%-increase counter A1:M1 displayed in B6. Strategy: compute
   the number in Python, write the VALUE (v0 beats emulating VBA).

## Harness implications

- v0 values-first wins most tasks: graded cells are compared AFTER recalc, so writing correct
  values passes even when the instruction asks for "a formula". Formulas (v1 with `_xlfn.` prefix)
  only needed where the grader inspects formula text (rare) — verify per task.
- Serializer must include: values (capped 20k chars), sheet names exact, merged/fill info
  for formatting-gated tasks, and data-table bounds for 10k-row sheets (truncate + note it).
- Executor needs: datetime/time parsing, bottom-up deletes, dict-dedupe, set ops across sheets.
- Verifier second pass: re-read written cells + recompute via independent path (pandas vs loops).
- Time budget per task matters more for 10k-row sheets than for model tokens.
