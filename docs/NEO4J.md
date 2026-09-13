# tieout — Neo4j knowledge graph

**Every cell tied to its source — now as a queryable graph, and read back to ground the agent.**

## What was built (the judged delta)

tieout's tagline is *"every cell tied to its source,"* but until now that lineage lived only as
flat JSON (`exceptions.json` → `evidence_rows`) and per-call JSONL traces — recorded, not
connected or queryable. This makes the lineage a real **property graph** in Neo4j Aura and closes
the loop by **reading it back** to ground the agent's bank-counterparty matches.

Two directions, both **graceful-optional** (mirrors `harness/weave_hooks.py`):

```
WRITE  run pipeline / simulate
  → every answer cell becomes a stable (:Cell) identity node
  → tied to the source cells it derived from (DERIVED_FROM)
  → linked to the vendor it matched (MATCHES) and the exception it routed to (ROUTED_TO)

READ   before filling column K (bank counterparty)
  → lexical GraphRAG: Jaccard token-overlap scan of the seeded (:Vendor) memory
  → only normalised-exact candidates are offered as writable; the rest rank as near-misses
  → candidate matches injected into the prompt under "## Graph context"
```

If `NEO4J_URI` is unset, the driver is missing, or Aura is paused, **everything no-ops** and the
pipeline behaves byte-identically to before: same `exceptions.json`, same prompts, same scores.
The graph layer can never break the queue, the offline demo, the self-improvement loop, or the
Docker ship container (`neo4j` is imported lazily, inside `init_graph()`).

When it *is* enabled, `write_exceptions()` stamps `graph: {backend, run_id, lineage}` onto that
task's `exceptions.json` entry — after `write_lineage()` returns `True`, and only when enabled, so
the disabled artifact stays byte-identical. That `run_id` is what lets a replay land on the original
`CloseRun` instead of forking run history. A configured-but-unreachable instance fails fast (~1.4s
for a DNS miss, ~5s ceiling) and prints one `[tieout] graph disabled: …` line to stderr rather than
disabling silently — a paused Aura instance is no longer indistinguishable from an unconfigured one.

## Schema

```
                    (:CloseRun {run_id,task_id,status,mandate})
                          |  PRODUCED {value,status}        \  RAISED
                          v                                  v
  (:Sheet)<-IN_SHEET-(:Cell kind=answer  ref="Staging Sheet!K5")-ROUTED_TO->(:Exception {reason,status})
                          |  \
              DERIVED_FROM     MATCHES {method,score}          EVIDENCED_BY
                          |        \                                |
                          v         v                               v
        (:Cell kind=source)   (:Vendor {vendor_key,name,        (:EvidenceRow
         "Staging Sheet!J5"     clean_name,jurisdiction})         {sheet,row,key})
```

**Stable-identity nodes** — MERGEd by natural key, shared across runs (this is the *memory*):

| Node | Key (UNIQUE) | Props |
|------|--------------|-------|
| `Vendor` | `vendor_key` = normalize(`clean_name`) | `name, clean_name, jurisdiction (LU/Non-LU), legal_entity_domain, source_list (vendor-master\|related-party), variants[] (every spelling of the identity, primary first — 535 across 510 nodes), norm_key, norm_clean` |
| `Sheet` | `name` | — |
| `Cell` | `ref` (`"Staging Sheet!K5"`) | `sheet, coord, row, col, header, kind(answer\|source), value, last_run_id, last_status, first_seen, updated_at` |
| `EvidenceRow` | `(sheet, row, key)` | — |

**Per-run nodes:**

| Node | Key (UNIQUE) | Props |
|------|--------------|-------|
| `CloseRun` | `(run_id, task_id)` | `model, mandate, status, reason, created_at` |
| `Exception` | `(run_id, cell_ref)` | `reason, proposed_value, status, created_at` |

**Edges:** `IN_SHEET`, `PRODUCED {value,status}` (run→answer cell), `DERIVED_FROM {key}`
(answer→source cell = the lineage), `MATCHES {method,score,run_id}` (answer→vendor),
`EVIDENCED_BY` (answer→evidence row), `ROUTED_TO` (answer→exception), `RAISED` (run→exception).

### Idempotency (why re-runs collapse instead of growing)

1. Cells/Sheets/Vendors are keyed by **natural identity**, so repeated demo runs MERGE onto the
   same nodes. Set `TIEOUT_RUN_ID=demo` to also collapse `CloseRun` onto one node.
2. Run-specific / changing values live on **edges** (`PRODUCED`, `MATCHES`) or via `SET` — never
   inside a MERGE pattern (a changed prop in MERGE would fork duplicate edges).
3. **UNIQUE constraints** are created on init: with `--concurrency 4`, two threads can MERGE the
   same node; the constraint turns the 2nd into a transient error the driver's managed transaction
   **auto-retries** ⇒ no duplicates.
4. **Vendors are created only by `demo/seed_graph.py`.** The write path resolves a vendor with
   `OPTIONAL MATCH` and links only if found — it never MERGE-creates one. So a written value that is
   not in the master produces a `Cell` + `DERIVED_FROM` but **no `MATCHES` edge and no skeleton
   vendor**. With the extended 510-identity seed all 13 values the bank-cp demo writes do resolve
   (13 `MATCHES` at `score 1.0`), so on this fixture the branch is exercised by the blank cells
   (K5/K13 — no value, no `vendor_key`) rather than by an unmatched name. The guarantee is what keeps
   `MATCHES` meaningful: it is only ever an assertion the master can back.

## Sponsor tool

| Tool | Use |
|------|-----|
| **Neo4j Aura** (`neo4j+s://`) | Lineage/provenance graph + persistent vendor memory; official `neo4j` Python driver, `driver.execute_query()` managed transactions |
| **Lexical GraphRAG** | Jaccard token-overlap `CONTAINS` scan over `Vendor.clean_name` (primary) + a `vendor_name_ft` full-text index as fallback, gated on normalised exactness — no embeddings, no vector index |

Substring scan beats full-text here: bank narratives are truncated (`"NIP LIT"`), and the constant
legal-entity token (`NIP`) matches every vendor, so full-text needs trailing wildcards to be useful.
Overlap-`DESC` ordering floats the discriminative token above the constant one — `"NIP PLATFORM
SOLUTIONS APS"` ranks its exact vendor 1.0. `"NIP LIT"` is the honest opposite: no seeded vendor
contains `LIT`, so every candidate ties at 0.333 on `NIP` alone. Nothing to float, nothing to trust
— which is the same reason K5 routes to a human instead of being filled. Any pulled name the scan
misses falls back to `vendor_name_ft` (`db.index.fulltext.queryNodes`, best-effort);
`seed_graph.py` awaits the index after seeding so it is query-ready and the fallback never returns
empty mid-demo.

The score is **Jaccard** — `overlap / (query tokens + candidate tokens − overlap)`, not
`overlap / query tokens`. Recall-only scoring lets a short pulled name score 1.0 against a much
longer, more specific entity (`"NORDVIK INFRASTRUCTURE ADVANCED"` vs
`"…Advanced Bioenergy Fund II SCSp"`), which are not the same counterparty. Ranking is not the gate
either: `exact` — identity after folding case, diacritics, punctuation and one closed legal-form token
(`norm_key`) — is what the block tells the model it may write. Folding is what makes exactness usable
at all, since the bank narrative `"S.A R.L."` and the master's `"S.à r.l."` are one entity. The legal-form
map is a single entry, `ltd` → `limited`, chosen by held-out counterfactual rather than by taste; see
below.

### The benchmark fixture's answer key is not in the sheet its instruction names

Established before claiming any retrieval win. `close-tieout-bank-cp` asks for column K (`Matched
Sender/Beneficiary`) to be filled "using the `'Vendor Master List'` sheet". Where the 13 golden
answers actually sit in the init workbook:

| source | golden answers it contains |
|---|---|
| `Vendor Master List` sheet — the one the instruction names | **1 of 13** (`NIP P/S`) |
| Staging col J, the stated input | 10 of 13, and only modulo folding (`NI ABF I SCSP` → `NI ABF I SCSp`) |
| Staging col L (`Related Party Match`) | **11 of 13 verbatim** — `build_fixtures.py` copies cols A–Y and blanks only K, so L leaks the key |
| the counterparty masters in Aura | 13 of 13 |

Absent from the fixture entirely: K7 `Trentbeck Audit - Lu` and K15
`Ulla B. Hillebrandt Consulting - Non-LU`. Two defects, both documented and neither fixed, because
the benchmark fixture stays untouched: the instruction names a sheet that can answer 1 of 13 rows,
and column L hands the key to anyone willing to copy a column the instruction never mentions.

This also corrects an earlier reading of the same runs. "The model only filled 2/15" is neither a
model deficit nor an information deficit. Followed literally, the named sheet supports one fill, so
2 filled / 13 blank was near the compliant ceiling — the model was right on every cell it could
justify and correctly refused the rest.

### Measured: OFF 3/15 → ON 13/15, and exactly what that proves

`demo/seed_graph.py` used to seed Aura from the fixture's own `Vendor Master List` tab — 71 vendors
that `serialize_workbook` already inlines in the prompt. Retrieving them back was a no-op by
construction, and that is what the first A/B measured. It now seeds from
`demo/reference_masters.json` (510 identities, 535 spellings, 24 with alternates; committed so the
graph is reproducible without `~/Downloads`), i.e. from the system of record rather than from the
workbook under test.

Live A/B against Aura (`Qwen/Qwen3.8-27B`, temp 0.0, `--path hybrid`, same fixture, nothing else
changed between arms):

| arm | seed | write gate | correct | filled | wrong fills | exceptions |
|---|---|---|---|---|---|---|
| `TIEOUT_GRAPHRAG=0` | — | — | 3/15 | 2/15 | 1 (K6) | 13 |
| graph ON, v1 | 71 (fixture tab) | advisory block | 3/15 | 2/15 | 1 (K6) | 13 |
| graph ON, v2 | 510 | `[exact]` or score ≥ 0.6, else blank | 12/15 | 12/15 | 2 (K6, K7) | 3 |
| graph ON, v3 | 510 | `MIN_SCORE=0.6` | 13/15 | 13/15 | 2 (K6, K7) | 2 |
| **graph ON, v4** | **510** | **normalised exactness** | **13/15** | 12/15 | 1 (K6) | 3 |

The previous revision of this file concluded from v1 that the read path was *"correct, traced, and
redundant"* below the point where the master stops fitting in context (`38796b9`). **That conclusion
is retracted.** The null result was a seeding bug — the graph held a copy of what the prompt already
inlined — not a property of fixture size. Once the seed is the real master, the read path moves the
score on a fixture whose master does fit in context.

v2 is why the shipped header defers to the workbook before it offers a candidate. Its floor
("an `[exact]` hit, or score ≥ 0.6, otherwise leave the cell blank") overrode a match the fixture's
own `Vendor Master List` already had: K16's pulled name is `"NIP LIT"`, whose best candidate
`NIP P/S` scores 0.333, so the model blanked a cell the sheet could answer. v4's header says use the
sheet where the sheet has a match, and K16 comes back.

The seam is verified, not assumed (OFF control vs the v4 arm): OFF prompt 11724 chars, ON 13740,
delta 2016 = the `## Graph context` block plus its newline, and the OFF prompt equals the ON prompt
with that block removed. `_graph_fragment("")` returns `""` so gated-off prompts stay byte-identical,
and the keyword gate leaves the other two fixtures (`close-tieout-le-map`,
`close-tieout-movements-rec`) with no graph section at all.

What the delta is attributable to. Column L already leaked 11 of 13 answers to *both* arms, so most
of the gain is the block authorising a name source the instruction does not mention — the model reads
L as data, not as permission. The one cell only the graph can supply is **K15**:
`Ulla B. Hillebrandt Consulting - Non-LU` appears nowhere in the fixture, and the ON arm fills it
correctly because the folded `[exact]` hit plus the header's "a jurisdiction suffix is part of the
value" tells it to write the suffixed spelling. That single cell is the irreducible evidence that
retrieval added information the prompt did not have.

Both misses are honest, and both are the same class — the right counterparty in a spelling that is not
the golden's. That class dominates the held-out residuals too (8 of 20 fills below), so it is a
systematic variant-selection problem rather than anything a memory of past resolutions would fix:

- **K6** — the graph offers `NIP PLATFORM SOLUTIONS APS - Non-LU` as primary and lists the golden
  unsuffixed spelling as an alternate. Nothing in the row discriminates them, so the model takes the
  primary. A rule preferring the shorter variant would fix K6 and break K15, which needs the suffix;
  that is tuning to the key, so it is left wrong.
- **K7** — `TRENTBECK AUDIT LUXEMBOURG` retrieves `Trentbeck Audit (score 0.667)` with no `[exact]`,
  so the conservative gate blanks it. v3's threshold filled it with the wrong variant instead: same
  score, one more confident wrong fill.

`MIN_SCORE` was deleted after being measured, not after being argued about. Held-out check: the 40
real staging rows after the fixture's 15 — the fixture is the first 15 rows with a pulled name, so
this is every row `build_fixtures.py` leaves out (35 carry a golden match in the source workbook; 3
repeat a pulled name the fixture also uses). Gate applied mechanically — fill with the best
candidate's primary name, else blank, no model in the loop:

| write gate | fills | string-exact | right identity (folded) | right entity, other spelling | **wrong entity** |
|---|---|---|---|---|---|
| normalised exactness | 20 | 9 | 12 | 8 | **0** |
| exactness or score ≥ 0.90 | 20 | 9 | 12 | 8 | **0** |
| exactness or score ≥ 0.60 | 32 | 9 | 12 | 8 | **11** |

Over all 55 real rows the shipped gate fills 31 times — 19 string-exact, 22 the right identity, 9 the
right entity in a different spelling, **0 a wrong entity** — and leaves 17 rows blank that have a
golden plus 7 blanks that are correct.

The 0.90 row is identical to exactness alone, so the threshold did no work except overfit 15 graded
cells. The 0.60 row buys 12 more fills and *not one* extra right-identity fill: 11 are a different
counterparty and one writes a value where the source workbook's own golden is blank. Exactness is
therefore the only gate that survived held-out data.

Two corrections to how these numbers were previously read in this file. **"Wrong fills" was
over-counted.** The 8 held-out residuals are the right counterparty carrying a currency suffix no
master entry has (`NI Ranfjord II SCSp` → golden `NI Ranfjord II SCSp - EUR`,
`NI GMF II Coöperatief U.A.` → golden `… U.A. - USD`). The entity is right and the string is not, so
the honest headline for the shipped gate is *zero wrong entities*, not *7 wrong fills*. **And the
blanks are not a retrieval failure.** In every one of the 17 the golden answer *is* in the seeded
master; what is missing is the narrative→entity link — `NIP CINNABAR APS` → `NIP PLATFORM SOLUTIONS
APS`, `NORDVIK INFRASTRUCTURE PARTNER` → `NIP P/S` — which is knowledge the graph does not hold and a
similarity score cannot invent. Read the two results together and the honest claim is narrow.
**3/15 → 13/15 is a single-task, 15-cell measurement on a fixture whose key leaks into the prompt,
taken with a model in the loop; the retrieval-only held-out number is 12/20 right identity with zero
wrong entities. Reproducible with the commands below; not a benchmark score.**

### One fold, added after being measured: `ltd` → `limited`

`norm_key` folds case, diacritics and punctuation, plus one closed legal-form map with a single
entry — because that is all the real data supports. Over the 40 held-out rows it takes exact-gated
fills 17 → 20 and right-identity fills 9 → 12 with the wrong-entity count unchanged; over all 55 rows,
28 → 31 and 19 → 22. The three new fills are three names — `NI V AZURITE HOLDCO LTD`,
`NI V FENWICK HOLDCO LTD.`, `NI V KALVIK TOPCO LTD.` — each matching a master entry spelled
`Limited`. Wider maps (`co`/`corp`/`inc`/`plc`) added nothing on top of it.

The benchmark cannot have been what this was tuned against: **no string in the fixture's 15 rows
contains `ltd`**, neither the pulled name nor the golden, so every fixture folded key is byte-identical
with and without the map and the fixture's graph block is unchanged at 2013 characters — the measured
13/15 stands without spending a re-run. A jurisdiction-token strip (`LUXEMBOURG` → `LU`) was measured
in the same pass and **rejected**: it turned K7's near-miss into a confident wrong fill,
`Trentbeck Audit` where the golden is `Trentbeck Audit - Lu`.

### Why there is no cross-period vendor-memory axis

The obvious next feature — let the graph remember that period 1 resolved `X` to `Y` and reuse it in
period 2 — was scoped, measured, and dropped:

- **A deterministic gate has nothing to learn from its own past.** Across all 55 rows there are 29
  distinct pulled names and *zero* names whose golden differs from row to row. Resolution depends only
  on the name, so if the gate fills a recurring name correctly in period 1 it already fills it
  correctly in period 2, and if it misses the name it missed it in period 1 too and has nothing to
  remember. Memory only earns its keep where resolution is human-corrected — which is the governed
  memory's job, not the graph's.
- **The ceiling is 7 cells anyway.** The best period split of the real sheet is 22/33 (or 25/30), and
  only 7 period-2 rows repeat a name period 1 already resolved — in all 7 the prior value equals the
  golden, i.e. a perfect score on rows the exactness gate already gets right.
- **It is the wrong subsystem.** `docs/COREWEAVE.md` assigns approved business rules — aliases,
  renames, "these two spellings are one counterparty" — to the governed SQLite memory, and states the
  Neo4j extension *"is not the authority for approved business rules"*. `demo/memory_scenario.py`
  already demonstrates cross-cycle learning there, with approval and provenance attached.
- **The keys are not scoped.** `Cell.ref` carries no tenant/workbook/version, so a prior-resolution
  read on the shared Aura instance would leak one fixture's answers into another's prompt. That is the
  boundary `docs/COREWEAVE.md` names, and closing it is a schema change, not a query.

What the graph can carry for that axis with no schema change is the *distinction*: `MATCHES.method` on
`(:Cell)-[:MATCHES]->(:Vendor)` is written today and only ever holds `'exact-value'`
(`harness/exceptions.py`), so a fill that came from an approved governed rule can be recorded as such
and told apart from a fill that came from similarity. That is the audit question a memory feature
actually has to answer.

What the graph carries regardless of retrieval is **provenance**: 75 `(:Cell)` nodes tied by 60
`DERIVED_FROM` edges to the sources they came from, 13 `MATCHES` edges into the master at
`score 1.0`, exceptions linked to their evidence rows, and identity that stays stable across runs —
`Cell` was still 75 after seven `CloseRun` writes during the A/B. The six experiment runs were
pruned afterwards, so the instance now holds exactly one `CloseRun` (`demo`), 75 `Cell`, 510
`Vendor`, 2 `Exception`, 9 `EvidenceRow`, 1 `Sheet`, zero skeleton vendors. That `demo` run is written
by `demo/simulate_demo.sh` — `status = 'ok: simulated golden'` — so its 15/15 is construction, not
model evidence; the A/B numbers above come from live model runs. The provenance is the *"every cell
tied to its source"* claim, and it is the part to demo.

```bash
uv run --directory research --extra graph python ../demo/seed_graph.py   # 510 vendors
cd research
TIEOUT_RUN_ID=ab-off TIEOUT_GRAPHRAG=0 uv run --extra graph python ../harness/pipeline.py \
  --dataset-dir ../demo/close-tieout --ids close-tieout-bank-cp --path hybrid --fresh \
  --out-dir /tmp/ab-off
TIEOUT_RUN_ID=ab-on TIEOUT_GRAPHRAG=1 uv run --extra graph python ../harness/pipeline.py \
  --dataset-dir ../demo/close-tieout --ids close-tieout-bank-cp --path hybrid --fresh \
  --out-dir /tmp/ab-on
```

The held-out gate table, the fold counterfactual and the recurrence numbers come from a separate
read-only tool — no model, no credits, no writes, but it does need the source workbook
(`--source`, or `YLOOKUP_DATASETS`):

```bash
research/.venv/bin/python demo/measure_gate.py            # add --detail for per-row classification
```

## Aura setup

1. Create a free **Aura** instance (Console → Create → Aura Free / Professional trial).
2. Copy the connection into `.env` (already gitignored — `.env.example` has empty placeholders):

   ```dotenv
   NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=...
   NEO4J_DATABASE=neo4j
   TIEOUT_GRAPH=1        # write lineage (default on when creds present)
   TIEOUT_GRAPHRAG=0     # read candidates into the prompt (default off)
   ```

   **Two different credentials, only one works here.** The Console also offers *Account Settings →
   Client credentials → Aura API* (a client id + client secret). Those mint an OAuth token for the
   **Aura management API** (`api.neo4j.io/oauth/token`) — they are not database credentials, and the
   bolt driver cannot use them: `auth=(user, password)` needs the instance's `neo4j` password. As a
   Basic pair against the Query API they return `Neo.ClientError.Security.Unauthorized`, and Bearer
   auth there requires your own SSO provider (Business Critical only). `NEO4J_PASSWORD` comes from
   the instance's **Connect** dialog, or the `Neo4j-<instance>-Created-<date>.txt` the Console
   downloads at creation; if it is lost, **Reset password** on the instance.

3. **Aura Free auto-pauses after a few days of inactivity**, and a long-inactive free instance can
   be **deleted** outright. Check the Console for the current window rather than trusting a number
   written here. Resume before demoing: `init_graph()` fails fast (`connection_timeout=5.0`) and
   prints `[tieout] graph disabled: …` to stderr if the instance is paused. If it was deleted,
   re-seed and rebuild — the graph is derived, so nothing is actually lost (next section).

## Durability: the graph is a derived index

The graph is **never the system of record**. Everything it holds is reconstructible from artifacts
tieout already writes — `exceptions.json` (status, reason, evidence rows), `outputs/*.xlsx` (the
written answer values) and the dataset (task metadata) — so losing the database loses no information:

```bash
cd research && uv run --extra graph python ../demo/rebuild_graph.py /tmp/syndicate-demo
```

`rebuild_graph.py` replays each task through the same `graph_payload()` the live run used, reading
the output workbook with `save=False` so finished artifacts are never rewritten (verified: output
SHA-256 and mtime unchanged across a rebuild). It replays onto the `run_id` stamped in the payload,
so rebuilding after a full wipe reproduces the original graph exactly — measured identical before
and after, and unchanged when run twice:

```
Cell 75 · Vendor 510 · Sheet 1 · CloseRun 1 · Exception 2 · EvidenceRow 5
DERIVED_FROM 60 · EVIDENCED_BY 10 · IN_SHEET 75 · MATCHES 13 · PRODUCED 15 · RAISED 2 · ROUTED_TO 2
skeleton vendors 0
```

`MATCHES` was 2 against the old 71-vendor seed and is 13 against the real master: every value the
golden run writes now resolves, which is the write path saying the same thing the read path found.

Two recovery details: a payload whose recorded absolute `output` path no longer exists falls back to
`<out_dir>/outputs/<task_id>.xlsx`, so a run directory copied to another machine is still replayable;
and artifacts written before the stamp existed replay onto the current `TIEOUT_RUN_ID` and print a
warning — pass `--run-id` to pin them. (Unstamped replays fork run history, which is precisely why
the stamp exists.)

### Backend tiers

| Tier | Backend | Cost | Use |
|------|---------|------|-----|
| 0 | none (default) | $0 | Evals, `research/loop.py`, the Docker ship container — graph off, artifacts byte-identical |
| 1 | **Neo4j Community, self-hosted** (`bolt://` or `neo4j://`) | $0 | Durable local/dev graph: no account, no auto-pause, no auto-delete |
| 2 | **Aura** (`neo4j+s://`) | free tier → paid | Managed, multi-user, cross-run vendor memory — the demo and the collaboration story |

Tiers 1 and 2 are the **same code path**: `init_graph()` passes `NEO4J_URI` verbatim to
`GraphDatabase.driver()`, so moving between them is a config edit, not a migration. One constraint —
the read path uses `routing_=RoutingControl.READ`, so the scheme must be routing-capable
(`neo4j+s://` or `neo4j://`; not `bolt+s://`).

There is deliberately **no SQLite backend for the lineage graph.** SQLite is already the governed
business-memory store (`harness/memory_store.py`: corrections → candidate rules → validated →
activated → revoked, event-sourced), and `docs/COREWEAVE.md` keeps the two subsystems apart — the
business-memory path does not contact Neo4j, the Neo4j extension is not the authority for approved
business rules, and a live graph is never migrated implicitly. A second SQLite concern for lineage
would blur exactly that boundary. Durability therefore comes from replay rather than mirroring: the
graph is reproducible from artifacts you already keep, and a free self-hosted Neo4j (tier 1) covers
the "must not vanish" case with no new code.

## Commands

```bash
# 1. seed the counterparty memory (510 identities from demo/reference_masters.json;
#    regenerate that file with --dump-masters if the source datasets are available)
cd research && uv run --extra graph python ../demo/seed_graph.py

# 2a. WRITE lineage offline (no API key — reliable on stage); TIEOUT_RUN_ID collapses re-runs
TIEOUT_RUN_ID=demo ./demo/simulate_demo.sh close-tieout-bank-cp

# 2b. WRITE + READ live (Tinker); GraphRAG carries candidate vendors into the prompt
TIEOUT_GRAPHRAG=1 ./demo/run_demo.sh close-tieout-bank-cp

# 3. READ from the CLI (the GraphRAG retrieval, no inference)
cd research && uv run --extra graph python ../harness/graph.py query "NIP LIT"

# 3b. MEASURE the read path on all 55 real rows (no inference, read-only; needs the source workbook)
research/.venv/bin/python demo/measure_gate.py

# 4. REBUILD from artifacts (recovery after an Aura pause/delete, or moving backend tier)
cd research && uv run --extra graph python ../demo/rebuild_graph.py /tmp/syndicate-demo
```

Run graph demos with `uv run --extra graph` (the `neo4j` driver is an optional extra; the
Dockerfile `pip install`s only its 3 pinned packages and is unaffected).

## Demo Cypher (Neo4j Browser / Aura console)

Lineage for one answer cell — K5 tied to its source, its run, and the exception it raised
(K5/K13 are the two unresolved cells in the golden bank-cp workbook):

```cypher
MATCH (c:Cell {ref: 'Staging Sheet!K5'})-[r]-(n) RETURN c, r, n;
```

Why K5 routed to review (the exception + the evidence rows behind it):

```cypher
MATCH (c:Cell {ref: 'Staging Sheet!K5'})-[:ROUTED_TO]->(e:Exception)
OPTIONAL MATCH (c)-[:EVIDENCED_BY]->(ev:EvidenceRow)
RETURN c.value AS answer, e.reason, e.status, collect(ev) AS evidence;
```

Contrast — a resolved cell K16 linked to its vendor (the "memory" edge; K6 → `NIP PLATFORM
SOLUTIONS APS`, K16 → `NIP P/S`):

```cypher
MATCH (c:Cell {ref: 'Staging Sheet!K16'})-[m:MATCHES]->(v:Vendor)
RETURN c.value, m.method, m.score, v.name, v.jurisdiction;
```

The vendor memory the read path queries, and the lineage written by one run:

```cypher
MATCH (v:Vendor) WHERE v.clean_name CONTAINS 'NIP' RETURN v.name, v.jurisdiction LIMIT 10;
MATCH (r:CloseRun {run_id: 'demo'})-[:PRODUCED]->(c:Cell) RETURN r.task_id, count(c);
```

Confirm idempotency after re-running twice with `TIEOUT_RUN_ID=demo` — counts must not move, and
there must be zero skeleton vendors:

```cypher
MATCH (c:Cell) RETURN count(c);
MATCH (v:Vendor) RETURN count(v);
MATCH (v:Vendor) WHERE v.name IS NULL RETURN count(v);  // expect 0
```

## Architecture

```
harness/graph.py        lazy neo4j driver + schema DDL + WRITE_CYPHER + lexical SCAN + CLI
harness/exceptions.py   graph_payload() builds lineage from the INIT workbook; write hook + stamp
harness/pipeline.py     init_graph()/close_graph(); GraphRAG read (keyword+flag gated) → prompt
harness/prompts.py      _graph_fragment() — "## Graph context" seam (byte-identical when empty)
demo/seed_graph.py      seeds (:Vendor) from demo/reference_masters.json (510 identities)
demo/reference_masters.json  committed counterparty master — the seed, so no ~/Downloads needed
demo/rebuild_graph.py   replays a run's artifacts back into the graph (recovery / tier move)
demo/simulate_demo.sh   offline write path (uv run --extra graph; init_graph in the heredoc)
demo/run_demo.sh        live path (uv run --extra graph; TIEOUT_GRAPHRAG=1 turns on the read)
```

The write hook lives in **one** place — `write_exceptions()` — so it covers both the live pipeline
and the offline simulate path. The review CLI does not call `write_exceptions`, so there is no
double-write. The read is gated by `TIEOUT_GRAPHRAG` (default off) **and** a keyword
(`vendor|counterparty|beneficiary|sender`), so non-vendor tasks and `research/loop.py`'s
hill-climbing measurement are never perturbed.

## Out of scope

- Native **vector index** / embeddings for fuzzy vendor matching (adds an embedding API + a network
  dependency on stage; ~$0 at this data size but higher demo risk).
- **Human-review write-back**: approve/reject as `(:Exception)-[:RESOLVED_BY]->…`. The graph records
  the pre-review `status` (`pending`) only. Easy follow-on (second hook in `_apply_decisions`).
