from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

HEADERS = ["Tenant", "Entity", "Account", "Currency", "Narrative", "Vendor Hint", "Date", "Amount"]
SCOPE = ["synthetic-tenant", "Example Fund A", "BANK-001", "EUR"]
VENDOR = "Example Services Ltd"


def write_workbook(path: Path, rows: list[list]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Transactions"
    ws.append(HEADERS)
    for row in rows:
        ws.append(row)
    with path.open("xb") as stream:
        wb.save(stream)
    wb.close()


def create_fixtures(out: Path) -> dict:
    from memory_workbook import load_records

    out.mkdir(parents=True, exist_ok=True)
    paths = {name: out / f"{name}.xlsx" for name in ("cycle1", "replay", "cycle2")}
    if any(path.exists() for path in paths.values()) or (out / "replay_cases.json").exists():
        raise FileExistsError("Use a new directory; synthetic fixtures are not overwritten")
    write_workbook(paths["cycle1"], [[*SCOPE, "EXAMPLE SERVICES", "", "2026-01-31", 120]])
    write_workbook(paths["replay"], [
        [*SCOPE, " example   services ", "", "2025-11-30", 85],
        [*SCOPE, "EXAMPLE SERVICES HOLDINGS", "", "2025-11-30", 40],
        ["synthetic-other-tenant", *SCOPE[1:], "EXAMPLE SERVICES", "", "2025-11-30", 85],
        [*SCOPE, "EXAMPLE SERVICES", "Different Services Ltd", "2025-11-30", 85],
        [SCOPE[0], "Example Fund B", *SCOPE[2:], "EXAMPLE SERVICES", "", "2025-11-30", 85],
        [*SCOPE[:2], "BANK-002", "EUR", "EXAMPLE SERVICES", "", "2025-11-30", 85],
        [*SCOPE[:3], "USD", "EXAMPLE SERVICES", "", "2025-11-30", 85],
    ])
    write_workbook(paths["cycle2"], [
        [*SCOPE, "EXAMPLE SERVICES HOLDINGS", "", "2026-02-28", 200],
        [*SCOPE, "Example    Services", "", "2026-02-28", 135],
        [*SCOPE, "EXAMPLE SERVICES", "Different Services Ltd", "2026-02-28", 70],
        ["synthetic-other-tenant", *SCOPE[1:], "EXAMPLE SERVICES", "", "2026-02-28", 300],
    ])
    labels = [VENDOR, None, None, None, None, None, None]
    cases = [
        {"case_id": f"synthetic-replay-{index}", "record": record, "expected_vendor": expected}
        for index, (record, expected) in enumerate(zip(load_records(paths["replay"]), labels, strict=True), 1)
    ]
    with (out / "replay_cases.json").open("x") as stream:
        stream.write(json.dumps(cases, indent=2) + "\n")
    return {"paths": paths, "cases": cases}


def run(out: Path) -> dict:
    from memory_store import MemoryStore
    from memory_workbook import export_suggestions, load_records

    if any((out / name).exists() for name in ("memory.sqlite3", "evidence.json", "cycle2-reviewed.xlsx")):
        raise FileExistsError("Use a new directory; existing demo artifacts are not overwritten")
    fixtures = create_fixtures(out)
    paths, cases = fixtures["paths"], fixtures["cases"]
    db = out / "memory.sqlite3"
    with MemoryStore(db) as store:
        first = load_records(paths["cycle1"])[0]
        next_records = load_records(paths["cycle2"])
        before = store.suggest(next_records)
        correction = store.record_correction(
            first, VENDOR, "synthetic-controller",
            "Synthetic demonstration: the supplied vendor master identifies this exact narrative as Example Services Ltd.",
        )
        rule = store.propose(correction["correction_id"])
        pending = store.suggest(next_records)
        report = store.validate(rule["rule_id"], cases, "synthetic-controller")
        if not report["eligible"]:
            raise AssertionError("synthetic replay should satisfy the local gate")
        store.activate(rule["rule_id"], "synthetic-controller")
        after = store.suggest(next_records)
        export_suggestions(paths["cycle2"], out / "cycle2-reviewed.xlsx", store)
        store.revoke(rule["rule_id"], "synthetic-controller", "Synthetic rollback demonstration")
        revoked = store.suggest(next_records)
        evidence = {
            "label": "Synthetic functional demonstration; not customer data or an independent effectiveness estimate",
            "rule": rule,
            "replay": report,
            "before": before,
            "candidate_not_active": pending,
            "after_approval": after,
            "after_revocation": revoked,
            "events": store.history(),
            "final_rule_status": "revoked",
            "expected_cycle2_vendors": [None, VENDOR, None, None],
        }
        assert all(row["vendor"] is None for row in before + pending + revoked)
        assert [row["vendor"] for row in after] == evidence["expected_cycle2_vendors"]
    with (out / "evidence.json").open("x") as stream:
        stream.write(json.dumps(evidence, indent=2) + "\n")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthetic two-cycle governed memory demonstration")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    result = run(Path(args.out_dir))
    print(json.dumps({"label": result["label"], "replay_eligible": result["replay"]["eligible"], "cycle2_vendors": [row["vendor"] for row in result["after_approval"]], "final_rule_status": result["final_rule_status"]}, indent=2))
