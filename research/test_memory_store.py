import hashlib
import importlib
import io
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "demo"))

openpyxl = importlib.import_module("openpyxl")
memory_store = importlib.import_module("memory_store")
memory_workbook = importlib.import_module("memory_workbook")
test_memory_policy = importlib.import_module("test_memory_policy")

MemoryStore = memory_store.MemoryStore
HEADERS = memory_workbook.HEADERS
REVIEW_SHEET = memory_workbook.REVIEW_SHEET
export_suggestions = memory_workbook.export_suggestions
load_records = memory_workbook.load_records
correction = test_memory_policy.correction
record = test_memory_policy.record
replay_cases = test_memory_policy.replay_cases

SCOPE_ROW = ["tenant-a", "entity-a", "account-a", "EUR"]


def write_workbook(path: Path, rows: list, headers=HEADERS, sheet="Transactions") -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(list(headers))
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()
    return path


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / "memory.sqlite3"
        self.store = MemoryStore(self.db)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _propose(self, **kwargs):
        payload = {key: value for key, value in correction(**kwargs).items() if key != "correction_id"}
        approved = self.store.record_correction(**payload)
        return self.store.propose(approved["correction_id"])

    def _activate(self, **kwargs):
        rule = self._propose(**kwargs)
        self.store.validate(rule["rule_id"], replay_cases(rule), "controller")
        self.store.activate(rule["rule_id"], "controller")
        return rule

    def test_db_permissions_and_parent_required(self):
        self.assertEqual(stat.S_IMODE(self.db.stat().st_mode), 0o600)
        with self.assertRaises(FileNotFoundError):
            MemoryStore(self.dir / "missing" / "x.sqlite3")

    def test_existing_file_permissions_untouched(self):
        existing = self.dir / "existing.sqlite3"
        existing.write_bytes(b"")
        os.chmod(existing, 0o644)
        with MemoryStore(existing):
            pass
        self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o644)

    def test_persistence_reopen(self):
        rule = self._propose()
        self.store.close()
        self.store = MemoryStore(self.db)
        rules = self.store.rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["status"], "candidate")
        self.assertEqual(rules[0]["rule"]["rule_id"], rule["rule_id"])
        kinds = [event["kind"] for event in self.store.history()]
        self.assertEqual(kinds, ["correction_approved", "rule_proposed"])

    def test_candidate_and_validated_rules_not_used(self):
        rule = self._propose()
        item = record()
        pending = self.store.suggest([item])
        self.assertEqual(pending[0]["decision"], "review")
        self.store.validate(rule["rule_id"], replay_cases(rule), "controller")
        still_pending = self.store.suggest([item])
        self.assertIsNone(still_pending[0]["vendor"])
        self.assertEqual(still_pending[0]["rule_ids"], [])

    def test_activation_without_replay_fails(self):
        rule = self._propose()
        with self.assertRaises(ValueError):
            self.store.activate(rule["rule_id"], "controller")

    def test_lead_scenario_replay_activation(self):
        from memory_scenario import create_fixtures

        fixtures = create_fixtures(self.dir / "scenario")
        paths, cases = fixtures["paths"], fixtures["cases"]
        first = load_records(paths["cycle1"])[0]
        approved = self.store.record_correction(first, "Example Services Ltd", "tester", "fixture correction")
        rule = self.store.propose(approved["correction_id"])
        report = self.store.validate(rule["rule_id"], cases, "tester")
        self.assertTrue(report["eligible"])
        self.store.activate(rule["rule_id"], "tester")
        after = self.store.suggest(load_records(paths["cycle2"]))
        self.assertEqual([row["vendor"] for row in after], [None, "Example Services Ltd", None, None])

    def test_revocation_survives_reopen_and_refuses_reactivation(self):
        rule = self._activate()
        self.store.revoke(rule["rule_id"], "controller", "rollback")
        self.store.close()
        self.store = MemoryStore(self.db)
        self.assertEqual(self.store.rules()[0]["status"], "revoked")
        with self.assertRaises(ValueError):
            self.store.activate(rule["rule_id"], "controller")
        with self.assertRaises(ValueError):
            self.store.validate(rule["rule_id"], replay_cases(rule), "controller")
        self.assertIsNone(self.store.suggest([record()])[0]["vendor"])

    def test_blank_reviewer_and_reason_rejected(self):
        payload = {key: value for key, value in correction().items() if key != "correction_id"}
        for key in ("vendor", "reviewer", "rationale"):
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.store.record_correction(**{**payload, key: "  "})
        rule = self._activate()
        with self.assertRaises(ValueError):
            self.store.activate(rule["rule_id"], " ")
        with self.assertRaises(ValueError):
            self.store.revoke(rule["rule_id"], "controller", "")
        with self.assertRaises(ValueError):
            self.store.revoke(rule["rule_id"], "", "reason")

    def test_stale_report_forces_revalidation(self):
        first = self._propose()
        second = self._propose(narrative="SECOND SERVICES", vendor="Second Services Ltd")
        self.store.validate(first["rule_id"], replay_cases(first), "controller")
        self.store.validate(second["rule_id"], replay_cases(second), "controller")
        self.store.activate(first["rule_id"], "controller")
        with self.assertRaises(ValueError):
            self.store.activate(second["rule_id"], "controller")
        self.store.validate(second["rule_id"], replay_cases(second), "controller")
        self.store.activate(second["rule_id"], "controller")
        statuses = {entry["rule"]["rule_id"]: entry["status"] for entry in self.store.rules()}
        self.assertEqual(statuses[second["rule_id"]], "active")

    def test_conflicting_active_rule_not_promoted(self):
        first = self._activate(vendor="Example Services Ltd")
        rival = self._propose(vendor="Other vendor")
        report = self.store.validate(rival["rule_id"], replay_cases(rival), "controller")
        self.assertFalse(report["eligible"])
        with self.assertRaises(ValueError):
            self.store.activate(rival["rule_id"], "controller")
        suggestion = self.store.suggest([record()])[0]
        self.assertEqual(suggestion["decision"], "suggested")
        self.assertEqual(suggestion["vendor"], "Example Services Ltd")
        self.assertEqual(suggestion["rule_ids"], [first["rule_id"]])

    def test_already_active_activation_error(self):
        rule = self._activate()
        with self.assertRaises(ValueError):
            self.store.activate(rule["rule_id"], "controller")

    def test_missing_objects_explicit(self):
        with self.assertRaises(KeyError):
            self.store.propose("missing-correction")
        for call in (
            lambda: self.store.validate("missing", replay_cases(self._propose()), "c"),
            lambda: self.store.activate("missing", "c"),
            lambda: self.store.revoke("missing", "c", "r"),
        ):
            with self.assertRaises(KeyError):
                call()

    def test_local_operations_only(self):
        self._activate()
        self.assertNotIn("neo4j", sys.modules)
        self.assertNotIn("graph", sys.modules)


class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / "memory.sqlite3"
        self.store = MemoryStore(self.db)
        self.src = write_workbook(self.dir / "cycle.xlsx", [
            [*SCOPE_ROW, "EXAMPLE SERVICES", "", "2026-01-31", 120],
            [None] * 8,
            [*SCOPE_ROW, "OTHER NARRATIVE", "hint", "2026-01-31", 5],
        ])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_load_records_and_stable_hash(self):
        records = load_records(self.src)
        self.assertEqual(len(records), 2)
        sha = hashlib.sha256(self.src.read_bytes()).hexdigest()
        self.assertEqual(records[0]["record_id"], f"{sha}:Transactions:2")
        self.assertEqual(records[0]["source"], {"workbook_sha256": sha, "sheet": "Transactions", "cell": "E2"})
        self.assertEqual(records[0]["vendor_hint"], "")
        self.assertEqual(records[1]["vendor_hint"], "hint")
        self.assertEqual([r["record_id"] for r in load_records(self.src)], [r["record_id"] for r in records])

    def test_header_validation(self):
        missing = write_workbook(self.dir / "missing.xlsx", [[*SCOPE_ROW, "N", "", "d", 1]], headers=HEADERS[:-1])
        with self.assertRaisesRegex(ValueError, "Amount"):
            load_records(missing)
        dup = write_workbook(self.dir / "dup.xlsx", [[*SCOPE_ROW, "N", "", "d", 1, "x"]], headers=[*HEADERS, "Tenant"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_records(dup)
        wrong_sheet = write_workbook(self.dir / "sheet.xlsx", [[*SCOPE_ROW, "N", "", "d", 1]], sheet="Other")
        with self.assertRaisesRegex(ValueError, "Transactions"):
            load_records(wrong_sheet)
        with self.assertRaisesRegex(ValueError, "xlsx"):
            load_records(self.dir / "nope.csv")

    def test_sparse_workbook_far_row(self):
        path = self.dir / "sparse.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(HEADERS)
        far = 50000
        for col, value in enumerate([*SCOPE_ROW, "EXAMPLE SERVICES", "", "d", 1], 1):
            ws.cell(row=far, column=col).value = value
        wb.save(path)
        wb.close()
        records = load_records(path)
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["record_id"].endswith(f":Transactions:{far}"))
        self.assertEqual(records[0]["source"]["cell"], f"E{far}")

    def test_formula_and_nontext_policy_fields_rejected(self):
        path = self.dir / "formula.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(HEADERS)
        ws.append([*SCOPE_ROW, "EXAMPLE SERVICES", "", "d", 1])
        ws.cell(row=2, column=5).value = "=1+1"
        wb.save(path)
        wb.close()
        with self.assertRaisesRegex(ValueError, "row 2"):
            load_records(path)
        numeric = write_workbook(self.dir / "numeric.xlsx", [[1, "entity-a", "account-a", "EUR", "N", "", "d", 1]])
        with self.assertRaisesRegex(ValueError, "Tenant"):
            load_records(numeric)

    def _activate_rule(self, vendor):
        approved = self.store.record_correction(load_records(self.src)[0], vendor, "controller", "fixture")
        rule = self.store.propose(approved["correction_id"])
        self.store.validate(rule["rule_id"], replay_cases(rule), "controller")
        self.store.activate(rule["rule_id"], "controller")
        return rule

    def test_export_exclusive_and_source_untouched(self):
        self._activate_rule("Example Services Ltd")
        before = self.src.read_bytes()
        destination = self.dir / "out.xlsx"
        suggestions = export_suggestions(self.src, destination, self.store)
        self.assertEqual(self.src.read_bytes(), before)
        self.assertTrue(destination.exists())
        self.assertEqual(suggestions[0]["decision"], "suggested")
        with self.assertRaises(FileExistsError):
            export_suggestions(self.src, destination, self.store)
        with self.assertRaises(ValueError):
            export_suggestions(self.src, self.src, self.store)
        wb = openpyxl.load_workbook(destination)
        try:
            ws = wb[REVIEW_SHEET]
            self.assertEqual([c.value for c in ws[1]][:5], ["Record ID", "Source SHA256", "Source Sheet", "Source Cell", "Decision"])
            self.assertEqual(ws.max_row, 3)
        finally:
            wb.close()

    def test_export_rejects_non_xlsx_destination(self):
        destination = self.dir / "out.csv"
        with self.assertRaises(ValueError):
            export_suggestions(self.src, destination, self.store)
        self.assertFalse(destination.exists())

    def test_export_reads_source_once(self):
        original = self.src.read_bytes()
        changed = io.BytesIO()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(HEADERS)
        ws.append(["tampered", "entity-a", "account-a", "EUR", "CHANGED", "", "d", 9])
        wb.save(changed)
        wb.close()
        reads = []
        real_read = Path.read_bytes

        def spy(path, *args, **kwargs):
            if Path(path) == self.src:
                reads.append(path)
                return original if len(reads) == 1 else changed.getvalue()
            return real_read(path, *args, **kwargs)

        destination = self.dir / "snap.xlsx"
        with mock.patch.object(Path, "read_bytes", spy):
            suggestions = export_suggestions(self.src, destination, self.store)
        self.assertEqual(len(reads), 1)
        sha = hashlib.sha256(original).hexdigest()
        self.assertTrue(all(s["record"]["record_id"].startswith(sha) for s in suggestions))
        out_wb = openpyxl.load_workbook(destination)
        try:
            self.assertEqual(out_wb["Transactions"].cell(row=2, column=1).value, "tenant-a")
            self.assertEqual(out_wb[REVIEW_SHEET].cell(row=2, column=2).value, sha)
        finally:
            out_wb.close()

    def test_export_refuses_existing_review_sheet(self):
        wb = openpyxl.load_workbook(self.src)
        wb.create_sheet(REVIEW_SHEET)
        wb.save(self.dir / "hasreview.xlsx")
        wb.close()
        with self.assertRaisesRegex(ValueError, REVIEW_SHEET):
            export_suggestions(self.dir / "hasreview.xlsx", self.dir / "out2.xlsx", self.store)

    def test_formula_like_vendor_written_as_literal_string(self):
        self._activate_rule("=1+1")
        destination = self.dir / "review.xlsx"
        export_suggestions(self.src, destination, self.store)
        wb = openpyxl.load_workbook(destination)
        try:
            ws = wb[REVIEW_SHEET]
            cell = ws.cell(row=2, column=6)
            self.assertEqual(cell.value, "=1+1")
            self.assertEqual(cell.data_type, "s")
        finally:
            wb.close()


if __name__ == "__main__":
    unittest.main()
