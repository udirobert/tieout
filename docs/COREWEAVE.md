# tieout — CoreWeave Hacks

**Turn a controller's correction into tested, reusable reconciliation memory.**

The product goal is fewer recurring exceptions in the next close cycle, with
human approval and an inspectable decision history. A benchmark curve is
supporting research, not the customer outcome.

## Provenance and implementation boundary

The spreadsheet reconciliation engine, repair loop, exception queue, and original
CFO demo are disclosed prior work. The CoreWeave extension adds W&B Serverless
Inference, Weave operations/evaluations, prompt-skill experiments, and a governed
correction-memory workflow. The Neo4j lineage/vendor-retrieval extension is a
separate integration; it is not the authority for approved business rules.

Two kinds of learning must remain separate:

| Learning | Authority | Current implementation |
|---|---|---|
| Procedural skill text | Experimental evaluation | `research/loop.py`, injected into codegen prompts |
| Business mapping | Explicit reviewer correction and approval | Local `harness/memory_store.py` plus deterministic `memory_policy.py` |

The local business-memory path does not read model guesses as approved facts,
does not load the learned prompt overlay, and does not contact inference, Weave,
or Neo4j. The W&B-powered experimental loop remains available independently.
End-to-end sponsor tracing of the new review workflow is a follow-on, subject to
an explicit data-sharing policy; do not imply it already exists.

## Governed memory: the first product slice

```
import explicitly mapped workbook rows
  -> reviewer records a correction + rationale + source provenance
  -> immutable exact-alias candidate
  -> labeled replay: positive, near-name negative, conflicting evidence, scope boundaries
  -> explicit activation after replay gate
  -> next-period suggestions with rule IDs and review history
  -> revoke rule; future suggestions stop
```

- Rules require exact tenant, entity, account, and currency scope.
- Narrative matching normalizes case and whitespace only. No substring/fuzzy
  match, invented alias, or inferred accounting treatment is silently approved.
- Source identity includes the workbook SHA-256, sheet, and source cell.
- Corrections, rule definitions, validation, activation, and revocation are
  retained as local records/events. A replacement is a new rule ID, not an edit
  of the previous definition. `version=1` is per immutable rule; there is not yet
  a parent/child policy-version management UI.
- Candidate/validated rules do not influence suggestions. Activation reruns the
  replay under a transaction and refuses stale validation after active rules change.
- Conflicting vendor evidence or conflicting rules produce `review`, not a match.
- Export creates a separate workbook with a `tieout review` sheet containing
  proposed vendors and provenance. It never overwrites the source, fills final
  accounting cells, or posts to a ledger. Revocation affects future suggestions;
  already exported files remain historical artifacts.

This is a local, single-operator prototype: reviewer names are self-attested,
not authenticated; scope checks are not an authorization system. SQLite events
are append-only through the application, not a tamper-proof audit ledger.

## Run the synthetic two-cycle demonstration

Run from the repository root after installing the existing research dependencies:

```bash
uv sync --directory research
DEMO_DIR=$(mktemp -d /tmp/tieout-memory-demo.XXXXXX)
uv run --directory research python ../demo/memory_scenario.py --out-dir "$DEMO_DIR"
uv run --directory research marimo run ../demo/console.py
```

In the console's picker choose `$DEMO_DIR/memory.sqlite3` under *governed memory
db* and one of `$DEMO_DIR/cycle*.xlsx` under *transactions workbook* — the picker
discovers both under `/tmp`, two levels deep, and the Memory tab's validate form
pre-fills `$DEMO_DIR/replay_cases.json`. Use a fresh output directory on every
scenario run; existing fixtures, databases, and export workbooks are not
overwritten.

Artifacts:

- `cycle1.xlsx`: the original correction source.
- `replay.xlsx` / `replay_cases.json`: explicitly labeled synthetic replay cases.
- `cycle2.xlsx`: changed period, amount, ordering, and narrative whitespace/case.
- `cycle2-reviewed.xlsx`: suggestions exported while the rule was active.
- `memory.sqlite3`: correction, candidate, replay, activation, and revocation history.
- `evidence.json`: before/candidate/active/revoked outputs and replay report.

The scripted scenario supplies a **synthetic reviewer** to exercise the API and
ends with the rule **revoked**, demonstrating rollback. It is not an unattended
production approval agent. In the workspace, record a new correction and propose
a new rule, validate it against the replay file, then explicitly activate it to
walk through the interactive lifecycle. Use a new export filename.

The demonstration's expected behavior is one recurring alias suggested after
activation, with the near-name, contradictory vendor, and other-tenant examples
remaining in review. This is a functional test, **not a customer accuracy claim,
a lockbox result, or evidence of learned fuzzy generalization**.

### Verification status

The policy/store/workbook suite passed 29 unit tests, covering replay gates,
activation/revocation, stale validation, scope boundaries, sparse sheets, source
snapshot consistency, and literal-string exports. The captured synthetic
scenario is `/tmp/tieout-memory-run-SEef/evidence.json`.

The revised callback-based marimo UI passed static checks, but its full extended
browser flow remains unverified. Browser testing was stopped at the user's
request due to CPU impact; the task's browser processes and marimo server were
shut down. The latest browser log contains a page-load timeout, not a completed
end-to-end pass. Earlier UI smoke evidence predates the callback rewrite and
must not be presented as verification of the revised UI. Use the saved scenario
and unit-test evidence; do not automatically restart browser testing.

`demo/console.py` was browser-verified once, under explicit permission, with this
boundary: all three tabs rendered against real artifacts (`/tmp/syndicate-demo`,
a governed-memory scenario dir), the picker loaded a run + db + workbook, and one
live Aura retrieval was submitted from the Graph tab. The review and
governed-memory write actions were **not** clicked in a browser; they were
exercised headlessly through the console's own form callbacks against scratch
copies with redirected output paths, which confirmed approve writes the proposed
value, reject reverts to init, unselected rows are untouched, and the aggregate
`exceptions.json` keeps its array shape. Rendering the Graph tab never connects:
`graph.configured()` inspects the environment only, because `graph.enabled()`
would ensure schema on page load.

### Workbook contract

Sheet: `Transactions`. Required headers (exact, unique):

`Tenant`, `Entity`, `Account`, `Currency`, `Narrative`, `Vendor Hint`, `Date`, `Amount`.

Scope/narrative are non-empty text. `Vendor Hint` may be blank; conflicting text
forces review. Formulas are rejected in matching/scope fields. Date and amount
are preserved context, not matching predicates in this version. This explicit
adapter does not assume the legacy CFO fixtures have these columns. The original
exception CLI and benchmark pipeline are unchanged; their output is not silently
connected to business memory.

## Hackathon demo narrative

1. Disclose the prior engine and the new work.
2. Show an unresolved recurring counterparty and its workbook source.
3. Record the controller's correction. Show the candidate is still inactive.
4. Inspect replay coverage, expected outcomes, and the confusing negative cases.
5. Approve the rule explicitly, then open the second close cycle.
6. Show the recurring alias suggested, the lookalike still in review, and the
   reviewer/rationale/source behind the suggestion.
7. Revoke the rule and show that future reuse stops.
8. Show the separate W&B/Weave experimental loop as the research layer, not as
   proof that business corrections are automatically safe.

## Sponsor tooling and research commands

| Tool | Implemented role |
|---|---|
| W&B Serverless Inference | Runtime and mutator via `wandb:` adapter |
| Weave | Model/pipeline operation traces and per-iteration evaluations |
| marimo | `demo/console.py` — one tabbed surface (Run / Memory / Graph); legacy `loop_dashboard.py` and `close_workspace.py` remain |
| Neo4j | Optional existing lineage and lexical vendor retrieval; see `NEO4J.md` |

```bash
# Research runs use .env WANDB_API_KEY; paid inference may be consumed.
./scripts/sweep.sh research/data/spreadsheetbench_verified_400 15
uv run --directory research python loop.py \
  --dataset-dir data/spreadsheetbench_verified_400 --sample 20 --iters 3 \
  --model wandb:Qwen/Qwen3.8-27B --out-dir /tmp/tieout-loop-new-run
uv run --directory research marimo run ../demo/console.py   # Run tab: loop curve + exception queue
```

Never run concurrent experimental loops against the shared
`harness/skills_overlay.json`. Historical outputs must be retained in distinct
run directories. No new benchmark run is necessary for the offline memory demo.

## Historical exploratory results — not a validated sales claim

These are the previously recorded single-run results, retained for transparency.
The default samples were the first N tasks, not random population samples.

| Model, dev-15 | hybrid | values |
|---|---:|---:|
| Qwen/Qwen3.8-27B | 0.9232 | 0.5164 |
| deepseek-ai/DeepSeek-V4-Flash-0731 | 0.9162 | 0.5100 |
| meta-llama/Llama-3.3-70B-Instruct | 0.6344 | 0.5414 |

This compares execution configurations, not an isolated experiment on repair.
The values path also has retries. Model ranking on 15 tasks does not establish
an overall winner or justify changing configurations to obtain a better story.

| dev-20 iteration | Qwen cell accuracy | decision | Llama cell accuracy | decision |
|---|---:|---|---:|---|
| baseline | 0.9964 | baseline | 0.6599 | baseline |
| 1 | 0.9954 | reverted | 0.7494 | kept |
| 2 | 0.9288 | reverted | 0.8919 | kept, audit flag |
| 3 | 0.9234 | reverted | 0.8407 | reverted |

Llama's observed best-minus-baseline delta was 23.20 percentage points. Its task
pass rate moved from 8/20 to 10/20. Qwen's 99.64% cell score accompanied only
14/20 passing tasks; it is not evidence that the workflow is solved. The overlay
is replaced between iterations, so two accepted iterations do not mean two
skills accumulated in the final library.

CFO demo scores were 0.7447 for Qwen and 0.9149 for Llama, each 2/3 tasks passing.
**That dataset had already been used for model comparison and troubleshooting.**
It is a regression/demo set, not an untouched lockbox. Llama also previously
scored 0.9149 on it without this learned overlay. The final score alone therefore
does not establish transfer or incremental benefit.

### Read-only audit of the saved Llama outputs

`research/audit_loop.py` re-scores saved workbooks without inference or
recalculation, checks the recorded results, and captures output/reference/scorer
hashes. The initial audit is saved locally at
`/tmp/tieout-llama-audit-governed-memory.json`; use that capture rather than
recomputing inputs when presenting these findings.

| Iteration | Task-balanced accuracy | Improved tasks vs baseline | Regressed tasks vs baseline |
|---|---:|---:|---:|
| baseline | 60.64% | 0 | 0 |
| 1 | 63.30% | 1 | 3 |
| 2 (selected) | 63.97% | 3 | 3 |
| 3 | 63.95% | 3 | 2 |

All four saved runs graded all 20 tasks without missing/error outputs under the
current scorer, reproducing their recorded aggregate scores. All 20 tasks are
sheet-level tasks. Two workbooks contribute approximately 74.64% of the 15,960
scored cells. In the selected run, task `23-24` contributes 3,713 additional
correct cells; the net change across all tasks is 3,703. Thus essentially all
net cell-level gain is concentrated in one workbook, while the task-balanced
increase is approximately 3.33 percentage points. This is not evidence that
most workflows improved, nor does output replay establish causal attribution.

The historical loop did not preserve complete immutable skill/config manifests,
so the audit cannot reconstruct a controlled counterfactual from its logs.

### Known measurement limitations and next experiment

- Mutation and selection currently use the same dev tasks; temp-0 paired tasks
  reduce some variation but do not remove nondeterminism or selection bias.
- Cell accuracy is micro-averaged across cells; large workbooks dominate. Report
  task pass rate and task-balanced accuracy alongside it.
- `score_task` errors currently have no cell count and are omitted from the cell
  accuracy denominator. Report errors explicitly; do not treat exact-match
  grading as immunity to evaluator bugs or gaming.
- Mutator input includes expected/actual values. Generic-skill instructions are
  not a technical guarantee against memorization.
- `replaces` routing currently suppresses a base skill before checking the
  replacement's keywords; the documented inherited gating is not implemented.
  Audit/fix this before interpreting skill deltas as controlled effects.
- The >10-point flag logs suspicion but does not block promotion. It is not an
  audited release gate. The new business-memory activation gate is separate.
- Local historical runs lacked LibreOffice recalculation. Values/formula paths
  can be affected differently, so comparisons are not automatically unbiased.

Next research gate: freeze code/model/config and immutable skill versions;
partition by workbook/task family into mutation, selection, and genuinely fresh
final test sets before optimizing; repeat paired incumbent/candidate runs;
audit per-task improvements/regressions and grading errors; run baseline and
selected candidate on the final set only after selection. Repeat inspection or
retuning consumes the test set. These steps remain follow-on research work,
not capabilities claimed by the current greedy loop.

## Commercial wedge and pilot

**Customer hypothesis:** fund administrators or outsourced finance teams doing
recurring bank-to-counterparty reconciliation in Excel. Willingness to pay and
workflow fit still need customer discovery.

**Offer:** keep the workbook process; tieout proposes matches, identifies the
exceptions requiring judgment, and reuses approved decisions in the next close.
Start with one workflow in a paid, human-reviewed pilot, not autonomous close.

Pilot sequence:

1. Agree data permissions and one reconciliation workflow with its process owner.
2. Label approved historical corrections and confusing negatives; retain a later
   period for evaluation before proposing rules.
3. Replay historical periods, then shadow the next close without ledger posting.
4. Compare reviewer minutes, correct recurring resolutions, incorrect suggestions,
   unresolved/reopened exceptions, and audit-record completeness. Agree targets
   with the customer before measuring; do not invent ROI from synthetic data.
5. Decide whether a paid expansion is justified by observed value.

Before real customer data: authentication/roles, storage and tenant access
isolation, retention/deletion/export policy, encryption/backup choices, audit
integrity, and explicit inference/tracing data-sharing consent. The existing
Neo4j cell keys also need tenant/workbook/version scoping before multi-client
use. Do not migrate a live graph implicitly or call scoped matching an access
control boundary.

Out of scope for this slice: ERP write-back, production multi-tenancy, fuzzy
alias auto-approval, fine-tuning, unattended policy changes, and a claimed
production efficiency gain.
