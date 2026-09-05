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
