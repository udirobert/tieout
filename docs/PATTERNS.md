# Patterns & principles — ready for Sat 12:00 init

Principles only, no provenance. All text-only, no installs.

## Harness backbone

- Hybrid prompting: chain-of-thought (512 tokens) for hard types, direct (128–256) for easy.
  Reason sheet-level/manipulation tasks, direct cell lookups.
- Tiered `max_new_tokens` per type + adaptive time guard: `remaining < n_left*8s` → FAST MODE
  (96 tokens, direct). The judges' run is timed; never exceed budget.
- Greedy decode (`do_sample=False`). Beam search caused catastrophic failures in past runs.
- Lenient parser (biggest free win): early versions dropped ~5% answers starting with
  common words. Never filter model output aggressively — parse first `{...}` block, strip `<think>`.
- Never blank: always emit a best guess; partial credit beats zero.
- Dual output paths: absolute (`/out/predictions.jsonl`) + local backup copy.
- Keep the base tokenizer; don't re-save one from a newer library version.
- Sampling nondeterminism (±few tasks between runs) is expected — report shipped-scorer numbers.

## Code-execution loop

- `write script -> run (subprocess, timeout) -> parse SUMMARY_JSON -> iterate <=3`.
- Script must print exactly one line `SUMMARY_JSON=<json>` with a default-str serializer
  so numeric scalars never crash the encoder. Accept a run with valid SUMMARY_JSON even if
  the process crashes afterwards — evidence produced is what matters.
- Mandatory positive control: same computation on a known-answer synthetic case; if the
  control fails, verdict is `inconclusive`, never a forced pass.
- Summary validator rejects self-contradictory verdicts (failed control + claimed verdict,
  NaN/None metrics, zero measurable points). Rejected → inconclusive + logged.
- Attempt numbering continues across rounds; subset re-runs merge into the existing report,
  never wipe prior results. Rerunning a `--ids` subset must not delete other outputs/traces.
- Reviewer corrections file loaded at the start of each re-audit; reference-implementation
  escalation: after model attempts, if the outcome isn't supported, the reference wins.
  Principle: second derivation wins over first guess.
- Timeouts: CPU-fast design per script, 4000-char tail cap on stdout+stderr.

## Findings discipline

- Single canonical findings builder (unreconciled + overdue + imbalance + integrity risks).
  Never invent a second detector — all surfaces read one builder.
- Evidence-backed lines: every finding carries the rows that caused it.
  Trace `tool_output` must carry those rows.
- Writes are approve-gated; pipeline is read-only by default. Never mutate `/data`;
  only write to `/out`. Human sign-off story for the write-up.

## Deterministic workbook surgery

- `openpyxl.load_workbook(path, read_only=True)`, seeded RNG, regenerates identically.
- Header-tolerant ingest (real exports vary by casing/columns) — code computes after mapping.
- ID-grouped analysis (e.g. transaction/basket grouping). Map to range/cell grouping.
- Planted rise/fall/attach signals for demos. Map to synthetic fine-tune variations with known deltas.

## Verification receipt

- Deterministic rules decide, model only narrates. Receipt JSON: `schemaVersion`,
  `receiptType`, `status/verified`, `evidenceHash`, `attestedAt`, plus writeback fields.
  Per-task receipt lives in the trace (`verified`, `evidenceHash` = input hash);
  `predictions.jsonl` status mirrors the `verified` boolean.

## Import UX (product demo only, not scoring)

- 5 steps: Upload → Column Mapping → Preview → Confirm → Complete; auto-delimiter +
  quoted-field CSV/TSV; column-mapping auto-detect; preview → atomic commit.
  Only needed if showing a fund-demo import lane.

## Mandate + commitment

- Gated mandate + pre-write SHA-256 commitment → post-write reconcile against verifiable data.
  Principle: commit to intended answer cells before writing, reconcile after.

## What NOT to do

- No heavy orchestration frameworks (unattended container, space cost).
- No full document-parsing engines (scoring is xlsx-only).
- No extra model weights (fixed model, space + overfit risk).
- No chains, OAuth, or private env. Principles only.
