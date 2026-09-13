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
  → lexical GraphRAG: token-overlap scan of the seeded (:Vendor) memory
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
| `Vendor` | `vendor_key` = normalize(`clean_name`) | `name, clean_name, jurisdiction (LU/Non-LU), legal_entity_domain` |
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
   `OPTIONAL MATCH` and links only if found — it never MERGE-creates one. So an answer value that
   is not in the master (a fund name like `NI ABF I SCSp`) produces a `Cell` + `DERIVED_FROM` but
   **no `MATCHES` edge and no skeleton vendor**. That is the intended, honest behaviour.

## Sponsor tool

| Tool | Use |
|------|-----|
| **Neo4j Aura** (`neo4j+s://`) | Lineage/provenance graph + persistent vendor memory; official `neo4j` Python driver, `driver.execute_query()` managed transactions |
| **Lexical GraphRAG** | Token-overlap `CONTAINS` scan over `Vendor.clean_name` (primary) + a `vendor_name_ft` full-text index as fallback — no embeddings, no vector index |

Substring scan beats full-text here: bank narratives are truncated (`"NIP LIT"`), and the constant
legal-entity token (`NIP`) matches every vendor, so full-text needs trailing wildcards to be useful.
Overlap-`DESC` ordering floats the discriminative token above the constant one — `query "NIP
PLATFORM SOLUTIONS APS"` ranks its exact vendor 1.0. `"NIP LIT"` is the honest opposite: no seeded
vendor contains `LIT`, so every candidate ties at 0.5 on `NIP` alone. Nothing to float, nothing to
trust — which is the same reason K5 routes to a human instead of being filled. Any pulled name the
scan misses falls back to `vendor_name_ft` (`db.index.fulltext.queryNodes`, best-effort);
`seed_graph.py` awaits the index after seeding so it is query-ready and the fallback never returns
empty mid-demo.

### Measured: what the read path does and does not change

A live A/B against Aura (`Qwen3.8-27B`, temp 0.0, `--path hybrid`, same task both arms) — graph ON
vs `TIEOUT_GRAPHRAG=0`:

| | `## Graph context` in prompt | prompt len | cells filled | exceptions |
|---|---|---|---|---|
| graph ON | yes — 779 chars, 7 pulled names, scored candidates | 12504 | **2/15** | 13 |
| graph OFF | no | 11724 | **2/15** | 13 |

Identical cell values in both arms (`K6`, `K16`), so at temp 0.0 the retrieval changed **nothing
measurable**. The seam itself is clean: the 780-char delta is exactly the injected block plus one
newline, and the OFF arm carries no graph section at all.

The reason is structural, not a bug: this fixture's entire `Vendor Master List` (71 rows) already
sits inline in the baseline prompt, so `NIP P/S` and `NIP PLATFORM SOLUTIONS APS` are readable
without Neo4j. Retrieving them from the graph duplicates what the model can already see. **GraphRAG
earns its keep only once the master stops fitting in context** — below that threshold it is correct,
traced, and redundant. Claim otherwise would be unsupported by these runs.

What the graph does demonstrably carry on this fixture is **provenance**: 75 `(:Cell)` nodes tied by
60 `DERIVED_FROM` edges to the sources they came from, exceptions linked to their evidence rows, and
identity that stays stable across runs (three `CloseRun` nodes written, `Cell` still 75, `Vendor`
still 71). That is the *"every cell tied to its source"* claim, and it is the part to demo.

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
Cell 75 · Vendor 71 · Sheet 1 · CloseRun 1 · Exception 2 · EvidenceRow 5
DERIVED_FROM 60 · EVIDENCED_BY 10 · IN_SHEET 75 · MATCHES 2 · PRODUCED 15 · RAISED 2 · ROUTED_TO 2
skeleton vendors 0
```

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
# 1. seed the vendor-master memory (71 vendors from the fixture's 'Vendor Master List')
cd research && uv run --extra graph python ../demo/seed_graph.py

# 2a. WRITE lineage offline (no API key — reliable on stage); TIEOUT_RUN_ID collapses re-runs
TIEOUT_RUN_ID=demo ./demo/simulate_demo.sh close-tieout-bank-cp

# 2b. WRITE + READ live (Tinker); GraphRAG carries candidate vendors into the prompt
TIEOUT_GRAPHRAG=1 ./demo/run_demo.sh close-tieout-bank-cp

# 3. READ from the CLI (the GraphRAG retrieval, no inference)
cd research && uv run --extra graph python ../harness/graph.py query "NIP LIT"

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
demo/seed_graph.py      seeds (:Vendor) from the fixture's 'Vendor Master List'
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
