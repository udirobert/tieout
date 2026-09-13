#!/usr/bin/env python3
"""Seed the tieout counterparty knowledge graph into Neo4j (Aura).

The graph must hold the *system of record*, not a copy of what the fixture
workbook already inlines. Seeding from the fixture's own 'Vendor Master List'
sheet gives the read path nothing the prompt does not already have — which is
why the first GraphRAG A/B measured no delta.

So the default source is demo/reference_masters.json: the real Vendor Master
List (245) plus Related Party Master (296), extracted from the upstream
anonymised workbook by --dump-masters and committed, so seeding never depends
on ~/Downloads. Col K of the bank-counterparty task draws on both lists.

Falls back to the fixture sheet when the artifact is absent, so the original
seed-then-query demo still works on a fresh clone.

Vendors are created ONLY here — harness/graph.py never MERGE-creates a Vendor,
so a written value that is not in the master links to nothing (no skeleton nodes).
Idempotent: MERGE on vendor_key, so re-seeding updates in place.

Usage:
  cd research && uv run --extra graph python ../demo/seed_graph.py
  cd research && uv run --extra graph python ../demo/seed_graph.py --dump-masters
  cd research && uv run --extra graph python ../demo/seed_graph.py [init.xlsx]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))

import openpyxl  # noqa: E402

import graph  # noqa: E402

DEFAULT_FIXTURE = (
    ROOT
    / "demo/close-tieout/spreadsheet/close-tieout-bank-cp"
    / "1_close-tieout-bank-cp_init.xlsx"
)

DEFAULT_SRC = Path.home() / "Downloads" / "Ylookup Hackathon Datasets"
SOURCE_WORKBOOK = (
    "01-bank-statements-to-journal-entries/workbook/"
    "Bank statement to journal entries - working file (anonymised).xlsx"
)
# Both are 'Legal Entity Domain' | name, and both feed col K of the staging sheet.
REFERENCE_SHEETS = {
    "Vendor Master List": "vendor-master",
    "Related Party Master": "related-party",
}
MASTERS_JSON = ROOT / "demo" / "reference_masters.json"

_SEED_CYPHER = """
UNWIND $vendors AS v
MERGE (n:Vendor {vendor_key: v.vendor_key})
SET n.name = v.name, n.clean_name = v.clean_name,
    n.jurisdiction = v.jurisdiction, n.legal_entity_domain = v.domain,
    n.source_list = v.source_list, n.variants = v.variants,
    n.norm_key = v.norm_key, n.norm_clean = v.norm_clean
"""


def _vendor_sheet(wb):
    for ws in wb.worksheets:
        if "vendor" in ws.title.lower():
            return ws
    return None


def _entries_from_sheet(ws, source_list: str) -> list[dict]:
    """Col A = Legal Entity Domain, col B = name. Blank name rows exist upstream."""
    out = []
    for r in range(2, ws.max_row + 1):
        domain = ws.cell(row=r, column=1).value
        name = ws.cell(row=r, column=2).value
        if not isinstance(name, str) or not name.strip():
            continue
        out.append(
            {
                "name": name.strip(),
                "domain": domain.strip() if isinstance(domain, str) else "",
                "source_list": source_list,
            }
        )
    return out


def dump_masters(source_dir: Path) -> int:
    """Extract the upstream reference lists into the committed JSON artifact."""
    workbook = source_dir / SOURCE_WORKBOOK
    if not workbook.exists():
        print(f"source workbook not found: {workbook}")
        return 1
    wb = openpyxl.load_workbook(workbook, data_only=True)
    try:
        entries: list[dict] = []
        for sheet, source_list in REFERENCE_SHEETS.items():
            if sheet not in wb.sheetnames:
                print(f"  missing sheet: {sheet}")
                continue
            found = _entries_from_sheet(wb[sheet], source_list)
            print(f"  {sheet}: {len(found)} names")
            entries.extend(found)
    finally:
        wb.close()

    # Group by vendor_key: the key is jurisdiction-agnostic, so 'Trentbeck Audit'
    # and 'Trentbeck Audit - Lu' are one identity with two spellings. Grading is
    # exact string match, so every spelling has to survive — keep them as variants.
    grouped: dict[str, dict] = {}
    for entry in entries:
        key = graph.vendor_key(entry["name"])
        if not key:
            continue
        slot = grouped.setdefault(key, {**entry, "variants": []})
        if entry["name"] not in slot["variants"]:
            slot["variants"].append(entry["name"])
    deduped = list(grouped.values())

    MASTERS_JSON.write_text(
        json.dumps(
            {
                "source": workbook.name,
                "sheets": list(REFERENCE_SHEETS),
                "entries": deduped,
            },
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    by_list = {
        label: sum(1 for e in deduped if e["source_list"] == label)
        for label in set(REFERENCE_SHEETS.values())
    }
    multi = sum(1 for e in deduped if len(e["variants"]) > 1)
    print(
        f"wrote {len(deduped)} unique counterparties to "
        f"{MASTERS_JSON.relative_to(ROOT)} "
        f"({', '.join(f'{k}={v}' for k, v in sorted(by_list.items()))}; "
        f"{multi} with alternate spellings)"
    )
    return 0


def _to_vendor_records(entries: list[dict]) -> list[dict]:
    records: dict[str, dict] = {}
    for entry in entries:
        name = entry["name"]
        key = graph.vendor_key(name)
        if not key:
            continue
        clean, jurisdiction = graph.split_vendor(name)
        existing = records.get(key)
        if existing is None:
            records[key] = {
                "vendor_key": key,
                "name": name,
                "clean_name": clean,
                "jurisdiction": jurisdiction,
                "domain": entry.get("domain", ""),
                "source_list": entry.get("source_list", "fixture"),
                "variants": list(entry.get("variants") or [name]),
                "norm_key": graph.norm_key(name),
                "norm_clean": graph.norm_key(clean),
            }
            continue
        for variant in entry.get("variants") or [name]:
            if variant not in existing["variants"]:
                existing["variants"].append(variant)
    return list(records.values())


def load_reference_vendors() -> list[dict] | None:
    """Counterparties from the committed artifact; None when it is absent."""
    if not MASTERS_JSON.exists():
        return None
    data = json.loads(MASTERS_JSON.read_text(encoding="utf-8"))
    return _to_vendor_records(data.get("entries") or [])


def load_vendors(path: Path) -> list[dict]:
    """Fixture-sheet fallback: the 'Vendor Master List' tab of a workbook."""
    wb = openpyxl.load_workbook(path, data_only=True)
    try:
        ws = _vendor_sheet(wb)
        if ws is None:
            raise SystemExit(f"no 'Vendor Master List' sheet in {path}")
        return _to_vendor_records(_entries_from_sheet(ws, "fixture"))
    finally:
        wb.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        help="fallback workbook to read a 'Vendor Master List' sheet from",
    )
    ap.add_argument(
        "--dump-masters",
        action="store_true",
        help=f"extract upstream reference lists into {MASTERS_JSON.name} and exit",
    )
    ap.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SRC,
        help="Ylookup dataset root for --dump-masters",
    )
    args = ap.parse_args()

    if args.dump_masters:
        return dump_masters(args.source)

    if args.fixture:
        if not args.fixture.exists():
            print(f"fixture not found: {args.fixture}")
            return 1
        vendors = load_vendors(args.fixture)
        origin = args.fixture.name
    else:
        vendors = load_reference_vendors()
        if vendors is None:
            vendors = load_vendors(DEFAULT_FIXTURE)
            origin = f"{DEFAULT_FIXTURE.name} (fixture fallback)"
        else:
            origin = MASTERS_JSON.name

    if not graph.init_graph():
        print(
            "graph disabled — set NEO4J_URI/NEO4J_USER/NEO4J_PASSWORD in .env "
            "(Aura), and resume the instance if it auto-paused."
        )
        return 1
    ok = bool(vendors) and graph.run_write(_SEED_CYPHER, {"vendors": vendors})
    if ok:
        # Full-text is eventually consistent — wait for vendor_name_ft so a
        # seed-then-query demo never returns empty. Best-effort: proc names differ
        # across Neo4j 4.x/5.x and run_write swallows errors, so seeding never fails.
        for _await in (
            "CALL db.awaitIndex('vendor_name_ft')",
            "CALL db.index.awaitIndex('vendor_name_ft')",
            "CALL db.index.fulltext.awaitEventuallyConsistentIndexRefresh()",
        ):
            graph.run_write(_await)
    graph.close_graph()
    if not ok:
        print("seed failed (no counterparties parsed, or the write errored)")
        return 1
    print(f"seeded {len(vendors)} counterparties from {origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
