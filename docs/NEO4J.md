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
Overlap-`DESC` ordering floats the discriminative token above the constant one. Any pulled name the
scan misses falls back to `vendor_name_ft` (`db.index.fulltext.queryNodes`, best-effort);
`seed_graph.py` awaits the index after seeding so it is query-ready and the fallback never returns
empty mid-demo.

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

3. **Aura Free auto-pauses after ~3 days.** Resume the instance in the Console before demoing —
   `init_graph()` fails fast (~5s, `connection_timeout=5.0`) and silently disables if it is paused.

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
harness/exceptions.py   _graph_payload() builds lineage from the INIT workbook; write hook
harness/pipeline.py     init_graph()/close_graph(); GraphRAG read (keyword+flag gated) → prompt
harness/prompts.py      _graph_fragment() — "## Graph context" seam (byte-identical when empty)
demo/seed_graph.py      seeds (:Vendor) from the fixture's 'Vendor Master List'
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
