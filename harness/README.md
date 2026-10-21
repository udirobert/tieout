# harness — tieout pipeline

`classify -> (sheet: codegen | cell: values-first) -> exec/write -> sanity + optional soffice -> repair <=3 -> fallback -> never blank`

**Syndicate demo path:** `pipeline.py --path hybrid` (repair loop + skills + exception routing).  
**Eval path:** `clone_run.py` (one-shot values-first, batch eval).  
Docs: `docs/SYNDICATE.md`, `docs/demo.md`.

Tinker Qwen3.8-27B is the default. 16k output tokens, temperature 0.
`wandb:<model>` routes to W&B Serverless Inference (thinking disabled via
chat_template_kwargs); Weave traces every call when WANDB_API_KEY is set.
`skills_overlay.json` (written by research/loop.py) adds/replaces skill
fragments at runtime — the self-improvement loop's mutation surface.

**Local (Syndicate demo):**

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp
cd research && uv run python ../harness/pipeline.py \
  --dataset-dir ../demo/close-tieout --out-dir /tmp/tieout-demo \
  --path hybrid --ids close-tieout-bank-cp
```

**Eval / Docker:**

```
cd research && uv run python ../harness/pipeline.py --dataset-dir /data --out-dir /out
cd research && uv run python ../harness/pipeline.py --dataset-dir ... --out-dir ... --ids 13-1,51-12 --fresh
```

`--resume` (default) skips ids already in `predictions.jsonl`. `--fresh` wipes the out-dir artifacts first.
`--path hybrid` (default, ship): cell values-only, sheet codegen-only.
Sheet codegen + LibreOffice `#ERR!` → values-first (C recalc-as-gate).
Pinned answer range: values-first keeps init values; codegen omits them (echo caused the cell dip).
`--path auto` adds one cross-path fallback. `--temperature` (default 0; B uses 0.7).

## Governed business memory (separate, local workflow)

`memory_policy.py` defines exact-alias matching and the labeled replay gate.
`memory_store.py` records corrections, immutable rules, validation, activation,
and revocation in local SQLite. `memory_workbook.py` imports an explicit
`Transactions` schema and exports suggestions to a new workbook without editing
source cells. `demo/console.py` (Memory tab) is the review UI;
`demo/close_workspace.py` is the legacy single-purpose one.

The original exception CLI and pipeline do not automatically write to this store.
No model guess, prompt-overlay change, or Neo4j match is an approved correction.
Reviewer names are self-attested; matching scope is not authentication or tenant
access isolation. See `docs/COREWEAVE.md` for the synthetic demo and pilot limits.

## Tenancy, the ledger, and the customer surface

Every store is bound to **one tenant**. `MemoryStore(path, tenant)` and
`DecisionLedger(path, tenant)` record their tenant in a `meta` table: opening a
file under a different tenant raises `TenantMismatch`, a write naming another
tenant raises `CrossTenantWrite`, and rows outside the tenant are never
returned by a read. One file per tenant, so retention, deletion, and export are
filesystem operations rather than a `WHERE` clause someone has to remember.

Review decisions are appended to the tenant's **ledger**
(`ledger.py`) before the workbooks are touched — append-only, so deleting the
run directory does not erase what was decided. `close_metrics.py` then measures
the close from what the queue and the ledger already hold.

`close_keeper/app.py` is the customer surface: load a close package, review the
queue with its evidence and diff, decide through the recorded write path, then
read the governed memory and the history. `demo/console.py` is the instrument an
engineer uses; `close_keeper/demo_app.py` is the key-free walkthrough. All
three write through `exceptions.apply_decisions`, and none has a third way to
change a workbook.

## Files

- `pipeline.py` — entry. Sheet-level: codegen loop then one values-first fallback. Cell-level: values-first then one codegen fallback. Default `--model tinker:Qwen/Qwen3.8-27B`.
- `adapters.py` — `tinker:<base>|<model_path>` primary; `gemini:<model>` spare. No OpenRouter.
- `prompts.py` — `SYSTEM_VALUES` / `CODEGEN_SYSTEM` + attribution-guided repair prompts.
- `executor.py` — subprocess sandbox in a temp dir (init copied in; goldens not visible). Import allowlist, timeout 120s, API keys stripped.
- `serializer.py` — 120×30 preview + fill-aware lines + pinned answer-range excerpt (survives the 20k cut).
- `parsing.py` — lenient JSON (keeps `Sheet1!B6`) and codegen fence parser.
- `verifier.py` — graded cells present + scalars + no `#ERR!`; soffice recalc when `SOFFICE` / LibreOffice exists, silent skip otherwise.
- `tracer.py` — `traces/<id>.jsonl`, one line per model call. Codegen steps add `tool`/`tool_output`.
- `exceptions.py` — post-run exception queue (`exceptions.json`) + human review CLI. `apply_decisions` is the one write path: it persists the decision (and appends to the ledger) *before* any workbook is touched.
- `evidence.py` — the shared model of a flagged cell: current value, proposed value, reason, source rows. Every surface renders this, so the CLI, the console, the walkthrough and the ledger cannot drift apart.
- `tenant.py` — who is acting: `Principal` carries the tenant, the subject and the capabilities. A seam, not an authentication system — `local_principal()` trusts whoever runs the process.
- `tenant_store.py` — the shared base for tenant-bound SQLite stores: one file per tenant, bound on first write and locked afterwards.
- `ledger.py` — the append-only decision ledger. Survives the workbook it describes; `export()` returns the tenant's whole record.
- `close_metrics.py` — what a close cost: exceptions raised, decisions, minutes in queue, reopened exceptions. Computed from the queue and the ledger.
- `weave_hooks.py` — Weave init gating + traceable op wrappers (no-op without WANDB_API_KEY)

After each task, `write_exceptions()` flags blank cells, `#N/A`, Excel errors, and review
sentinels (`EXCEPTION`, `REVIEW`). Review:

```bash
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
```

Offline demo (no Tinker): `./demo/simulate_demo.sh close-tieout-bank-cp` Keys via env only (`TINKER_API_KEY`, optional `GEMINI_API_KEY`).
