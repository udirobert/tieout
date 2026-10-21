"""The agent's write path — the same guarantee the other surfaces have.

The agent can approve and reject cells, so it can write to a workbook. That
makes it subject to the same two rules as the console and the close desk:

* one write path — `exceptions.apply_decisions`, and
* every decision appended to the tenant's ledger before the workbook is touched.

The second is the one the agent had been missing: it rewrote the workbooks and
recorded the decisions only in the mutable `exceptions.json`, so deleting the
run directory erased what had been decided. These tests pin the behaviour down.
"""

import importlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "close_keeper"))

exceptions_mod = importlib.import_module("exceptions")
ledger_mod = importlib.import_module("ledger")

TENANT = "acme"


class AgentWritePathTests(unittest.TestCase):
    """The agent's tools, exercised the way the agent calls them."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.run_dir = self.dir / "run"
        (self.run_dir / "outputs").mkdir(parents=True)
        self._seed_queue()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_queue(self):
        """A one-task queue with one exception, built the way the pipeline does."""
        import openpyxl

        init = self.run_dir / "init.xlsx"
        out = self.run_dir / "outputs" / "task.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws["A1"] = "Narrative"
        ws["B1"] = "Answer"
        ws["A2"] = "EXAMPLE SERVICES"
        wb.save(init)
        shutil.copy(init, out)

        task = {"id": "task", "init_xlsx": str(init), "answer_sheet": "Sheet1"}
        payload = {
            "task_id": "task",
            "init_xlsx": str(init),
            "output": str(out),
            "status": "ok: simulated",
            "reason": "",
            "exceptions": [
                {
                    "cell": "Sheet1!B2",
                    "reason": "empty answer cell",
                    "evidence_rows": [
                        {"sheet": "Sheet1", "row": 2, "key": "EXAMPLE SERVICES"}
                    ],
                    "proposed_value": "Example Services Ltd",
                    "current_value": "",
                    "raised_at": "2026-10-01T09:00:00+00:00",
                    "status": "pending",
                }
            ],
        }
        (self.run_dir / "exceptions.json").write_text(
            json.dumps([payload], indent=2), encoding="utf-8"
        )

    def test_apply_review_decisions_writes_to_the_ledger(self):
        """The agent's decision lands in the tenant's ledger, not just the queue."""
        from agent import apply_review_decisions

        result = apply_review_decisions(
            str(self.run_dir),
            {"task": {"Sheet1!B2": "approved"}},
            tenant=TENANT,
        )
        self.assertIn("applied 1 decision", result)

        ledger_path = self.run_dir / f"ledger-{TENANT}.sqlite3"
        self.assertTrue(ledger_path.exists(), "no ledger written")
        with ledger_mod.DecisionLedger(ledger_path, TENANT) as ledger:
            recorded = ledger.decisions()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["cell"], "Sheet1!B2")
        self.assertEqual(recorded[0]["decision"], "approved")
        self.assertEqual(recorded[0]["tenant"], TENANT)
        self.assertEqual(
            recorded[0]["evidence"][0]["key"], "EXAMPLE SERVICES"
        )

    def test_the_decision_survives_the_run_directory(self):
        """The point of the ledger: deleting the artefact erases neither."""
        from agent import apply_review_decisions

        apply_review_decisions(
            str(self.run_dir),
            {"task": {"Sheet1!B2": "approved"}},
            tenant=TENANT,
        )
        shutil.rmtree(self.run_dir / "outputs")
        (self.run_dir / "exceptions.json").unlink()

        with ledger_mod.DecisionLedger(
            self.run_dir / f"ledger-{TENANT}.sqlite3", TENANT
        ) as ledger:
            recorded = ledger.decisions()
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0]["cell"], "Sheet1!B2")

    def test_list_exceptions_shows_the_evidence_and_the_diff(self):
        """The agent sees the same cell, diff and source rows as every other surface."""
        from agent import list_exceptions

        listing = list_exceptions(str(self.run_dir))
        self.assertIn("Sheet1!B2", listing)
        self.assertIn("empty answer cell", listing)
        self.assertIn("Sheet1 r2 · EXAMPLE SERVICES", listing)
        self.assertIn("(blank) → Example Services Ltd", listing)

    def test_an_invalid_verdict_is_refused(self):
        from agent import apply_review_decisions

        result = apply_review_decisions(
            str(self.run_dir),
            {"task": {"Sheet1!B2": "maybe"}},
            tenant=TENANT,
        )
        self.assertIn("invalid verdict", result)
        self.assertFalse((self.run_dir / f"ledger-{TENANT}.sqlite3").exists())


if __name__ == "__main__":
    unittest.main()
