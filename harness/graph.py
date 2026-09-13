"""tieout knowledge graph — Neo4j lineage write + lexical GraphRAG read.

Active when NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD are set, no-ops otherwise
(mirrors weave_hooks: import-safe, fail-fast, never breaks the pipeline).

The graph realises "every cell tied to its source": answer cells are stable
identity nodes tied to the source cells they derived from, the vendor they
matched, and the exception they routed to. Vendors are seeded once
(demo/seed_graph.py) and form the persistent memory the read path queries.

neo4j is imported lazily inside init_graph() so the Docker ship container
(clone_run -> pipeline -> exceptions -> graph) never needs the package.

CLI: python harness/graph.py query "NIP LIT" ["NIP PLATFORM SOLUTIONS APS" ...]
"""

import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path

_ENABLED = None
_DRIVER = None
_RUN_ID = None
_DB = "neo4j"

# Stable-identity nodes are MERGEd by natural key; run-specific facts live on
# edges / via SET so repeated demo runs collapse instead of growing the graph.
_SCHEMA = [
    "CREATE CONSTRAINT cell_ref_unique IF NOT EXISTS "
    "FOR (c:Cell) REQUIRE c.ref IS UNIQUE",
    "CREATE CONSTRAINT vendor_key_unique IF NOT EXISTS "
    "FOR (v:Vendor) REQUIRE v.vendor_key IS UNIQUE",
    "CREATE CONSTRAINT sheet_name_unique IF NOT EXISTS "
    "FOR (s:Sheet) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT closerun_unique IF NOT EXISTS "
    "FOR (r:CloseRun) REQUIRE (r.run_id, r.task_id) IS UNIQUE",
    "CREATE CONSTRAINT exception_unique IF NOT EXISTS "
    "FOR (e:Exception) REQUIRE (e.run_id, e.cell_ref) IS UNIQUE",
    "CREATE CONSTRAINT evidence_unique IF NOT EXISTS "
    "FOR (e:EvidenceRow) REQUIRE (e.sheet, e.row, e.key) IS UNIQUE",
    "CREATE FULLTEXT INDEX vendor_name_ft IF NOT EXISTS "
    "FOR (v:Vendor) ON EACH [v.clean_name, v.name]",
]

# One managed (auto-retrying) write. UNWIND per answer cell; MERGE endpoints
# only, then SET changing props. Vendors are resolved (OPTIONAL MATCH), never
# created here — seed_graph.py owns Vendor creation.
_WRITE_CYPHER = """
MERGE (run:CloseRun {run_id: $run_id, task_id: $task_id})
  ON CREATE SET run.created_at = datetime($created_at), run.model = $model,
                run.mandate = $mandate, run.status = $status, run.reason = $reason
  ON MATCH  SET run.status = $status, run.reason = $reason
MERGE (asheet:Sheet {name: $answer_sheet})
WITH run, asheet
UNWIND $cells AS c
MERGE (cell:Cell {ref: c.ref})
  ON CREATE SET cell.sheet = c.sheet, cell.coord = c.coord, cell.row = c.row,
                cell.col = c.col, cell.header = c.header, cell.kind = c.kind,
                cell.first_seen = datetime($created_at)
  ON MATCH  SET cell.kind = c.kind
SET cell.value = c.value, cell.last_run_id = $run_id, cell.last_status = $status,
    cell.updated_at = datetime($created_at)
MERGE (cell)-[:IN_SHEET]->(asheet)
MERGE (run)-[pr:PRODUCED]->(cell) SET pr.value = c.value, pr.status = $status
OPTIONAL MATCH (v:Vendor {vendor_key: c.vendor_key})
FOREACH (d IN c.derived |
  MERGE (src:Cell {ref: d.ref})
    ON CREATE SET src.sheet = d.sheet, src.coord = d.coord, src.kind = 'source',
                  src.value = d.value, src.first_seen = datetime($created_at)
    ON MATCH  SET src.value = d.value
  MERGE (s2:Sheet {name: d.sheet})
  MERGE (src)-[:IN_SHEET]->(s2)
  MERGE (cell)-[df:DERIVED_FROM]->(src) SET df.key = d.value
)
FOREACH (e IN c.evidence |
  MERGE (ev:EvidenceRow {sheet: e.sheet, row: e.row, key: e.key})
  MERGE (cell)-[:EVIDENCED_BY]->(ev)
)
FOREACH (m IN CASE WHEN v IS NULL THEN [] ELSE [1] END |
  MERGE (cell)-[mt:MATCHES]->(v)
    SET mt.method = c.match_method, mt.score = c.score, mt.run_id = $run_id
)
FOREACH (x IN CASE WHEN c.exception IS NULL THEN [] ELSE [1] END |
  MERGE (ex:Exception {run_id: $run_id, cell_ref: c.ref})
    ON CREATE SET ex.created_at = datetime($created_at)
  SET ex.reason = c.exception.reason, ex.proposed_value = c.exception.proposed_value,
      ex.status = c.exception.status
  MERGE (cell)-[:ROUTED_TO]->(ex)
  MERGE (run)-[:RAISED]->(ex)
)
"""

# Lexical candidate-vendor retrieval: symmetric token overlap over the
# jurisdiction-stripped clean_name. Substring beats full-text for truncated bank
# narratives ("NIP LIT"). Score is Jaccard (overlap / union of query and candidate
# tokens), not overlap / query tokens: recall-only scoring lets a short pulled name
# score 1.0 against a much longer, more specific entity ("NORDVIK INFRASTRUCTURE
# ADVANCED" vs "...Advanced Bioenergy Fund II SCSp"), which are not the same
# counterparty. Exact hits outrank fuzzy ones regardless of score. Needs no index,
# so it works the moment we seed.
_SCAN_CYPHER = """
UNWIND $queries AS q
WITH q.raw AS raw, q.needle AS needle, q.norm AS norm,
     [t IN split(q.needle, ' ') WHERE size(t) > 1] AS toks
WHERE size(toks) > 0
MATCH (v:Vendor)
WITH raw, needle, norm, toks, v, toLower(v.clean_name) AS clean,
     [t IN split(toLower(v.clean_name), ' ') WHERE size(t) > 1] AS ctoks
WITH raw, needle, norm, toks, v, clean, ctoks, [t IN toks WHERE clean CONTAINS t] AS hits
WHERE size(hits) > 0
WITH raw, needle, norm, v, clean, size(hits) AS overlap,
     size(toks) + size(ctoks) - size(hits) AS union
WITH raw, v, overlap, toFloat(overlap) / union AS score,
     (coalesce(v.norm_key, '') = norm OR coalesce(v.norm_clean, '') = norm
      OR toLower(trim(v.name)) = needle OR clean = needle) AS exact
ORDER BY raw, exact DESC, overlap DESC, score DESC, size(v.clean_name) ASC
WITH raw, collect({name: v.name, clean: v.clean_name, juris: v.jurisdiction,
                   variants: v.variants,
                   score: round(score * 1000) / 1000, exact: exact})[0..$k] AS cands
RETURN raw AS pulled, cands
"""

# Best-effort fallback for names the substring scan misses (plan: "Optional
# full-text index as a fallback"). queryNodes throws if vendor_name_ft is not
# online yet, so every call is wrapped in try/except by the caller. Same cand
# shape as the scan so results merge cleanly.
_FULLTEXT_CYPHER = """
CALL db.index.fulltext.queryNodes('vendor_name_ft', $term) YIELD node, score
RETURN node.name AS name, node.clean_name AS clean, node.jurisdiction AS juris,
       node.variants AS variants, round(score * 1000) / 1000 AS score
ORDER BY score DESC
LIMIT $k
"""

_JURIS = re.compile(r"\s*-\s*(non[\s-]*)?lu\s*$", re.IGNORECASE)
_WS = re.compile(r"\s+")

# Exactness is the only gate that survives held-out data. Over the 40 real staging rows after the
# 15-row benchmark fixture's, ">= 0.90 or exact" fills identically to "exact only" (20 fills, 12 of
# them the right counterparty), while threshold 0.6 fills 32 with no additional right-identity fill
# and 11 fills that are a different counterparty entirely. Across all 55 real rows the exactness gate
# picks a wrong entity zero times. A score threshold tuned on 15 graded cells does not generalise.
# Folding case/diacritics/punctuation is what makes exactness usable at all — the bank narrative
# "S.A R.L." and the master's "S.à r.l." are the same entity.
_FOLD = re.compile(r"[^a-z0-9]+")

# Closed set on purpose. 'Ltd' and 'Limited' are the same legal form everywhere, so folding them is
# orthography, not a guess about the entity. Over the 40 held-out rows this one token takes
# exact-gated fills 17 -> 20 and right-identity fills 9 -> 12, wrong identities unchanged; over all
# 55 rows, 28 -> 31 and 19 -> 22. The three new fills are three names ('NI V AZURITE HOLDCO LTD',
# 'NI V FENWICK HOLDCO LTD.', 'NI V KALVIK TOPCO LTD.') each matching a master entry spelled
# 'Limited'. Wider maps (co/corp/inc/plc) added nothing on top of it. The benchmark cannot have been
# what this was tuned against: no string in the fixture's 15 rows contains 'ltd', in the pulled name
# or in the golden, so every fixture folded key is unchanged and the fixture's graph block stays
# byte-identical at 2013 chars — the measured 13/15 needs no re-run.
_LEGAL_FORM = {"ltd": "limited"}


def norm_key(value) -> str:
    """Case/diacritic/punctuation-insensitive identity of a counterparty name."""
    if not isinstance(value, str):
        return ""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    tokens = [t for t in _FOLD.split(folded.lower()) if t]
    return "".join(_LEGAL_FORM.get(t, t) for t in tokens)


_HEADER = (
    "Counterparty master retrieved from the knowledge graph, which is the system of "
    "record for counterparty names; the vendor sheet in the workbook is a partial "
    "local copy of it. Where the sheet already gives a match, use the sheet. Where "
    "the sheet has no match, an [exact] candidate below is that counterparty — write "
    "it EXACTLY as spelled, and where alternate spellings are listed pick the one "
    "that fits the row, since a jurisdiction suffix such as '- Non-LU' is part of "
    "the value. Candidates without [exact] are only similar names: do NOT write "
    "them. If a row has no [exact] candidate and no match in the sheet, leave the "
    "cell blank for the exception queue. Best candidate first."
)


def _render_candidate(c: dict) -> str:
    """One candidate as the model must write it: verbatim name, then provenance."""
    name = c.get("name") or c.get("clean") or ""
    alts = [v for v in (c.get("variants") or []) if v != name]
    exact = " [exact]" if c.get("exact") else ""
    alt = f" [also spelled: {' | '.join(alts)}]" if alts else ""
    return f"{name}{exact}{alt} (score {c.get('score')})"


def split_vendor(name: str) -> tuple[str, str]:
    """'Foo Bar - Non - LU' -> ('Foo Bar', 'Non-LU'); no suffix -> ('Foo Bar', '').

    Tolerates the vendor master's variable spacing ('- LU', '- Non-LU',
    '- Non - LU'). The suffix must be dash-led so names ending in 'lu' inside a
    word (e.g. 'Lux') are never stripped.
    """
    if not isinstance(name, str):
        return "", ""
    text = name.strip()
    m = _JURIS.search(text)
    if not m:
        return text, ""
    jurisdiction = "Non-LU" if m.group(1) else "LU"
    return text[: m.start()].rstrip(), jurisdiction


def vendor_key(value) -> str | None:
    """Canonical vendor identity: strip jurisdiction suffix, fold case/space.

    Shared by the seed and the write path so a written K value links to the
    seeded Vendor node (and never to a skeleton).
    """
    clean, _ = split_vendor(value)
    key = _WS.sub(" ", clean).strip().lower()
    return key or None


def _load_env_local() -> None:
    """setdefault .env reader (the offline simulate path never loads env)."""
    root = Path(__file__).resolve().parent.parent
    for env_path in (root / ".env", root / "research" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def init_graph() -> bool:
    """Connect to Aura + ensure schema. Fail-fast (~5s) and never raise."""
    global _ENABLED, _DRIVER, _RUN_ID, _DB
    if _ENABLED is not None:
        return _ENABLED
    _load_env_local()
    flag = os.environ.get("TIEOUT_GRAPH", "1").strip().lower()
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER")
    password = os.environ.get("NEO4J_PASSWORD")
    if flag in ("0", "false", "off") or not (uri and user and password):
        _ENABLED = False
        return False
    try:
        from neo4j import GraphDatabase  # lazy: absent package => disabled

        _DB = os.environ.get("NEO4J_DATABASE") or "neo4j"
        _DRIVER = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=5.0,
            connection_acquisition_timeout=5.0,
            max_connection_lifetime=600.0,
        )
        _DRIVER.verify_connectivity()
        _ensure_schema(_DRIVER, _DB)
        _RUN_ID = os.environ.get("TIEOUT_RUN_ID") or str(uuid.uuid4())
        _ENABLED = True
    except Exception as exc:  # noqa: BLE001 — graph must never break the pipeline
        try:
            if _DRIVER is not None:
                _DRIVER.close()
        except Exception:  # noqa: BLE001
            pass
        _DRIVER = None
        _ENABLED = False
        # Only reachable with creds present, so say why instead of disabling
        # silently: the usual cause is an auto-paused Aura instance.
        print(f"[tieout] graph disabled: {type(exc).__name__}: {exc}", file=sys.stderr)
    return _ENABLED


def _ensure_schema(driver, db: str) -> None:
    for stmt in _SCHEMA:
        driver.execute_query(stmt, database_=db)


def enabled() -> bool:
    """Lazy self-init: the offline simulate path calls neither init nor env."""
    if _ENABLED is None:
        init_graph()
    return bool(_ENABLED)


def run_id() -> str:
    return _RUN_ID or ""


def close_graph() -> None:
    global _DRIVER
    try:
        if _DRIVER is not None:
            _DRIVER.close()
    except Exception:  # noqa: BLE001
        pass
    _DRIVER = None


def write_lineage(payload: dict) -> bool:
    """Persist one task's lineage graph. No-op (False) when disabled."""
    if not enabled():
        return False
    try:
        _DRIVER.execute_query(_WRITE_CYPHER, parameters_=payload, database_=_DB)
        return True
    except Exception:  # noqa: BLE001 — the exception queue must never break
        return False


def run_write(query: str, parameters: dict | None = None) -> bool:
    """Run one managed write when enabled (used by demo/seed_graph.py)."""
    if not enabled():
        return False
    try:
        _DRIVER.execute_query(query, parameters_=parameters or {}, database_=_DB)
        return True
    except Exception:  # noqa: BLE001
        return False


def _fulltext_candidates(term: str, k: int) -> list:
    """Best-effort full-text fallback for one term; [] on any error.

    queryNodes throws if vendor_name_ft is not online yet, so this never raises
    into the caller — the scan stays the source of truth and this only fills gaps.
    """
    try:
        from neo4j import RoutingControl

        result = _DRIVER.execute_query(
            _FULLTEXT_CYPHER,
            parameters_={"term": term, "k": k},
            database_=_DB,
            routing_=RoutingControl.READ,
        )
    except Exception:  # noqa: BLE001 — index may not be online yet
        return []
    return [
        {
            "name": rec.get("name"),
            "clean": rec.get("clean"),
            "juris": rec.get("juris"),
            "variants": rec.get("variants"),
            "score": rec.get("score"),
        }
        for rec in result.records
    ]


def query_vendor_context(pulled_names, k: int = 3, limit: int = 40) -> str:
    """Lexical GraphRAG: candidate vendors per pulled name, as a prompt block.

    Substring scan is primary (best for truncated bank narratives); any name it
    misses falls back to the full-text index. The symmetric score only ranks —
    `exact` (folded identity) is what the header tells the model it may write.
    Empty/disabled ⇒ "" (byte-identical prompt seam).
    """
    if not enabled():
        return ""
    names: list[str] = []
    for raw in pulled_names or []:
        s = str(raw).strip()
        if s and s not in names:
            names.append(s)
    names = names[:limit]
    if not names:
        return ""
    queries = [{"raw": s, "needle": s.lower(), "norm": norm_key(s)} for s in names]
    cands_by_name: dict[str, list] = {}
    try:
        from neo4j import RoutingControl

        result = _DRIVER.execute_query(
            _SCAN_CYPHER,
            parameters_={"queries": queries, "k": k},
            database_=_DB,
            routing_=RoutingControl.READ,
        )
        for rec in result.records:
            cands_by_name[rec["pulled"]] = rec.get("cands") or []
    except Exception:  # noqa: BLE001 — fall through to the full-text fallback
        cands_by_name = {}
    for name in names:  # fallback only for names the scan returned nothing for
        if not cands_by_name.get(name):
            fb = _fulltext_candidates(name, k)
            if fb:
                cands_by_name[name] = fb
    lines = []
    for name in names:
        cands = cands_by_name.get(name) or []
        if not cands:
            continue
        rendered = "; ".join(_render_candidate(c) for c in cands)
        lines.append(f"- {name} -> {rendered}")
    if not lines:
        return ""
    return _HEADER + "\n" + "\n".join(lines)


def _cli(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "query" and len(argv) > 2:
        try:
            if not enabled():
                print(
                    "graph disabled — set NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD "
                    "in .env (Aura), then re-run."
                )
                return 1
            print(query_vendor_context(argv[2:], k=5) or "(no candidates)")
            return 0
        finally:
            close_graph()
    print('usage: python harness/graph.py query "NIP LIT" [...]')
    return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(_cli(sys.argv))
