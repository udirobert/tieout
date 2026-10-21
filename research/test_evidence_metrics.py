"""The evidence model and the close metrics — the review unit and its measures.

Two things are pinned here:

* the evidence model renders one thing the same way everywhere, so the CLI,
  the console and the walkthrough cannot drift apart, and
* the metrics report counts what it says it counts, and says so in words when
  a number is an upper bound rather than a measurement of effort.
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "demo"))

evidence_mod = importlib.import_module("evidence")
metrics_mod = importlib.import_module("close_metrics")
ledger_mod = importlib.import_module("ledger")
exceptions_mod = importlib.import_module("exceptions")

Decision = evidence_mod.Decision
EvidenceRow = evidence_mod.EvidenceRow
DecisionLedger = ledger_mod.DecisionLedger
measure_close = metrics_mod.measure_close
reopened_exceptions = metrics_mod.reopened_exceptions
decided_aliases = metrics_mod.decided_aliases


def _exception(**overrides) -> dict:
    base = {
        "cell": "Staging Sheet!K6",
        "reason": "no project match",
        "evidence_rows": [
            {"sheet": "Staging Sheet", "row": 6, "key": "NIP PLATFORM SOLUTIONS APS"}
        ],
        "proposed_value": "NIP PLATFORM SOLUTIONS APS",
        "current_value": "",
        "raised_at": "2026-10-01T09:00:00+00:00",
        "status": "pending",
    }
    base.update(overrides)
    return base


class EvidenceModelTests(unittest.TestCase):
    def test_label_is_defined_once(self):
        row = EvidenceRow("Staging Sheet", 6, "NIP PLATFORM")
        self.assertEqual(row.label, "Staging Sheet r6 · NIP PLATFORM")

    def test_blank_is_explicit_never_an_empty_string(self):
        decision = Decision(
            cell="Sheet1!K6",
            current_value="",
            proposed_value="",
            reason="empty answer cell",
        )
        self.assertEqual(decision.current_value, "(blank)")
        self.assertEqual(decision.diff_label, "(blank) → (blank)")

    def test_diff_shows_before_and_after(self):
        decision = Decision(
            cell="Sheet1!K6",
            current_value="Legal & Professional fees",
            proposed_value="433 Insurance",
            reason="recategorised",
        )
        self.assertEqual(
            decision.diff_label, "Legal & Professional fees → 433 Insurance"
        )

    def test_a_long_value_is_truncated_not_wrapped(self):
        decision = Decision(
            cell="Sheet1!K6",
            current_value="x" * 200,
            proposed_value="y",
            reason="long",
        )
        self.assertLess(len(decision.diff_label), 80)
        self.assertIn("…", decision.diff_label)

    def test_render_line_carries_the_evidence(self):
        decision = Decision.from_exception(_exception())
        line = decision.render_line()
        self.assertIn("Staging Sheet!K6", line)
        self.assertIn("no project match", line)
        self.assertIn("Staging Sheet r6", line)

    def test_evidence_label_says_so_when_there_is_none(self):
        decision = Decision.from_exception(_exception(evidence_rows=[]))
        self.assertEqual(decision.evidence_label, "no source rows found")

    def test_from_exception_keeps_the_raised_time(self):
        decision = Decision.from_exception(_exception())
        self.assertEqual(decision.raised_at, "2026-10-01T09:00:00+00:00")


class SurfaceParityTests(unittest.TestCase):
    """The point of the model: every surface renders the same decision."""

    def test_the_cli_and_the_row_renderer_agree(self):
        decision = Decision.from_exception(_exception())
        row = decision.as_row()
        self.assertEqual(row["cell"], decision.cell)
        self.assertEqual(row["reason"], decision.reason)
        self.assertEqual(row["current"], "(blank)")
        self.assertEqual(row["evidence"], decision.evidence_label)

    def test_the_ledger_record_carries_the_evidence_and_the_diff(self):
        decision = Decision.from_exception(_exception())
        record = decision.as_record()
        self.assertEqual(record["evidence"][0]["key"], "NIP PLATFORM SOLUTIONS APS")
        self.assertEqual(record["current_value"], "(blank)")
        self.assertEqual(record["proposed_value"], "NIP PLATFORM SOLUTIONS APS")


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _payload(self, status="approved", raised="2026-10-01T09:00:00+00:00"):
        return {
            "task_id": "close-tieout-bank-cp",
            "exceptions": [
                _exception(status=status, raised_at=raised),
            ],
        }

    def test_metrics_count_what_they_say(self):
        payloads = [self._payload()]
        with DecisionLedger(self.dir / "ledger.sqlite3", "acme") as ledger:
            decision = Decision.from_exception(payloads[0]["exceptions"][0])
            ledger.record(decision, reviewer="ann")
            metrics = measure_close(
                payloads, ledger=ledger, period="2026-10", dataset="fixture"
            )
        self.assertEqual(metrics.exceptions_raised, 1)
        self.assertEqual(metrics.decisions_recorded, 1)
        self.assertEqual(metrics.approved, 1)
        self.assertEqual(metrics.still_pending, 0)
        self.assertEqual(metrics.period, "2026-10")

    def test_pending_exceptions_are_counted_as_pending(self):
        metrics = measure_close([self._payload(status="pending")])
        self.assertEqual(metrics.exceptions_raised, 1)
        self.assertEqual(metrics.still_pending, 1)

    def test_minutes_in_queue_is_labelled_as_an_upper_bound(self):
        """The report must not imply it measured review effort."""
        payloads = [self._payload(raised="2026-10-01T09:00:00+00:00")]
        with DecisionLedger(self.dir / "ledger.sqlite3", "acme") as ledger:
            decision = Decision.from_exception(payloads[0]["exceptions"][0])
            ledger.record(decision, reviewer="ann")
            metrics = measure_close(payloads, ledger=ledger)
        self.assertIsNotNone(metrics.minutes_to_decide_median)
        self.assertTrue(
            any("upper bound" in note for note in metrics.notes),
            metrics.notes,
        )

    def test_reopened_exceptions_join_on_identity_not_cell_reference(self):
        """The same question must be recognised after it moves rows."""
        first = {
            "task_id": "close-1",
            "exceptions": [
                {
                    "cell": "Staging Sheet!K6",
                    "reason": "no project match",
                    "narrative": "NIP PLATFORM SOLUTIONS APS",
                    "scope": {
                        "tenant": "acme",
                        "entity": "Fund A",
                        "account": "BANK-001",
                        "currency": "EUR",
                    },
                    "status": "approved",
                }
            ],
        }
        second = {
            "task_id": "close-2",
            "exceptions": [
                {
                    "cell": "Staging Sheet!K99",  # moved rows
                    "reason": "no project match",
                    "narrative": "nip platform solutions aps",  # case folded
                    "scope": {
                        "tenant": "acme",
                        "entity": "Fund A",
                        "account": "BANK-001",
                        "currency": "EUR",
                    },
                    "status": "pending",
                }
            ],
        }
        identities = decided_aliases([first])
        reopened = reopened_exceptions([second], previous_aliases=identities)
        self.assertEqual(len(reopened), 1)
        self.assertEqual(reopened[0]["cell"], "Staging Sheet!K99")

    def test_a_different_account_is_not_a_reopen(self):
        first = {
            "task_id": "close-1",
            "exceptions": [
                {
                    "cell": "Sheet!K6",
                    "narrative": "NIP PLATFORM",
                    "scope": {
                        "tenant": "acme",
                        "entity": "Fund A",
                        "account": "BANK-001",
                        "currency": "EUR",
                    },
                    "status": "approved",
                }
            ],
        }
        second = {
            "task_id": "close-2",
            "exceptions": [
                {
                    "cell": "Sheet!K7",
                    "narrative": "NIP PLATFORM",
                    "scope": {
                        "tenant": "acme",
                        "entity": "Fund A",
                        "account": "BANK-002",
                        "currency": "EUR",
                    },
                    "status": "pending",
                }
            ],
        }
        reopened = reopened_exceptions(
            [second], previous_aliases=decided_aliases([first])
        )
        self.assertEqual(reopened, [])


if __name__ == "__main__":
    unittest.main()
