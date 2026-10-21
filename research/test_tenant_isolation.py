"""Tenant isolation — the guarantee that makes the store safe to hand a customer.

Two tenants must never see each other's rules, and neither may write into the
other's store. The tests here pin that behaviour down, because it is the kind
of property that stays true by accident right up until the first multi-tenant
deployment and then quietly stops being true.

The cases:

* a rule written for tenant A is invisible to tenant B's store,
* a record naming tenant B cannot be written into tenant A's store,
* reopening a store under a different tenant raises rather than serving rows,
* a file that predates tenant binding still opens and binds on first write,
* the decision ledger is isolated the same way the memory store is.
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))
sys.path.insert(0, str(ROOT / "demo"))

memory_store = importlib.import_module("memory_store")
ledger_mod = importlib.import_module("ledger")
evidence_mod = importlib.import_module("evidence")
tenant_mod = importlib.import_module("tenant")
test_memory_policy = importlib.import_module("test_memory_policy")

MemoryStore = memory_store.MemoryStore
DecisionLedger = ledger_mod.DecisionLedger
Decision = evidence_mod.Decision
Principal = tenant_mod.Principal
TenantMismatch = tenant_mod.TenantMismatch
CrossTenantWrite = tenant_mod.CrossTenantWrite
PermissionDenied = tenant_mod.PermissionDenied
local_principal = tenant_mod.local_principal

correction = test_memory_policy.correction
record = test_memory_policy.record
replay_cases = test_memory_policy.replay_cases

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"


def _record_for(tenant: str, narrative: str = "EXAMPLE SERVICES") -> dict:
    return record(narrative, tenant=tenant)


def _correction_for(tenant: str, narrative: str = "EXAMPLE SERVICES") -> dict:
    """The keyword arguments for `record_correction`, for a given tenant."""
    payload = correction(narrative, **{"tenant": tenant})
    payload.pop("correction_id", None)
    return payload


class TenantBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_binds_to_first_written_tenant(self):
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db) as store:
            self.assertIsNone(store.tenant)
            store.record_correction(**_correction_for(TENANT_A))
            self.assertEqual(store.tenant, TENANT_A)

    def test_reopening_under_a_different_tenant_raises(self):
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db) as store:
            store.record_correction(**_correction_for(TENANT_A))
        with self.assertRaises(TenantMismatch):
            MemoryStore(db, tenant=TENANT_B)

    def test_reopening_under_the_same_tenant_is_fine(self):
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db, tenant=TENANT_A) as store:
            store.record_correction(**_correction_for(TENANT_A))
        with MemoryStore(db, tenant=TENANT_A) as store:
            self.assertEqual(store.tenant, TENANT_A)
            self.assertEqual(len(store.corrections()), 1)
            self.assertEqual(len(store.history()), 1)

    def test_cross_tenant_write_is_refused(self):
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db, tenant=TENANT_A) as store:
            with self.assertRaises(CrossTenantWrite):
                store.record_correction(**_correction_for(TENANT_B))

    def test_a_rule_from_one_tenant_never_surfaces_for_another(self):
        """The load-bearing test: the rule fires for A and stays inert for B."""
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db, tenant=TENANT_A) as store:
            approved = store.record_correction(**_correction_for(TENANT_A))
            rule = store.propose(approved["correction_id"])
            store.validate(rule["rule_id"], replay_cases(rule), "controller")
            store.activate(rule["rule_id"], "controller")
            self.assertEqual(
                store.suggest([_record_for(TENANT_A)])[0]["decision"],
                "suggested",
            )

        # A second store, bound to another tenant, must not see the rule.
        other = self.dir / "other.sqlite3"
        with MemoryStore(other, tenant=TENANT_B) as store_b:
            self.assertEqual(store_b.rules(), [])
            self.assertEqual(
                store_b.suggest([_record_for(TENANT_B)])[0]["decision"],
                "review",
            )

    def test_legacy_file_without_tenant_binding_opens_and_binds(self):
        """A file written before this existed has no tenant; it binds on first write."""
        db = self.dir / "memory.sqlite3"
        with MemoryStore(db) as store:
            store.record_correction(**_correction_for(TENANT_A))
        with MemoryStore(db) as reopened:
            self.assertEqual(reopened.tenant, TENANT_A)
            self.assertEqual(len(reopened.corrections()), 1)


class PrincipalTests(unittest.TestCase):
    def test_capability_checks(self):
        reviewer = Principal(TENANT_A, "ann", roles=frozenset({"reviewer"}))
        self.assertTrue(reviewer.has("read"))
        self.assertTrue(reviewer.has("decide"))
        self.assertFalse(reviewer.has("govern"))
        with self.assertRaises(PermissionDenied):
            reviewer.require("govern")

    def test_local_principal_holds_every_capability(self):
        principal = local_principal()
        for capability in ("read", "decide", "teach", "govern", "administer"):
            self.assertTrue(principal.has(capability), capability)

    def test_unknown_capability_is_an_error_not_a_silent_false(self):
        with self.assertRaises(KeyError):
            Principal(TENANT_A, "ann").has("teleport")


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _decision(self, tenant: str = TENANT_A, cell: str = "Sheet1!K6") -> Decision:
        return Decision(
            cell=cell,
            current_value="(blank)",
            proposed_value="NIP PLATFORM SOLUTIONS APS",
            reason="no project match",
            evidence=(evidence_mod.EvidenceRow("Staging Sheet", 6, "NIP PLATFORM"),),
            status="approved",
            task_id="close-tieout-bank-cp",
            tenant=tenant,
        )

    def test_decisions_are_appended_in_order(self):
        with DecisionLedger(self.dir / "ledger.sqlite3", TENANT_A) as ledger:
            first = ledger.record(self._decision(cell="Sheet1!K6"))
            second = ledger.record(self._decision(cell="Sheet1!K7"))
            self.assertLess(first["decision_id"], second["decision_id"])
            self.assertEqual(len(ledger.decisions()), 2)

    def test_a_decision_survives_the_workbook_it_describes(self):
        """The ledger outlives the artefact — that is the point of it."""
        db = self.dir / "ledger.sqlite3"
        with DecisionLedger(db, TENANT_A) as ledger:
            ledger.record(self._decision())
        self.assertTrue(db.exists())
        with DecisionLedger(db, TENANT_A) as ledger:
            recorded = ledger.decisions()
            self.assertEqual(len(recorded), 1)
            self.assertEqual(recorded[0]["cell"], "Sheet1!K6")
            self.assertEqual(recorded[0]["evidence"][0]["key"], "NIP PLATFORM")

    def test_ledger_is_tenant_bound(self):
        db = self.dir / "ledger.sqlite3"
        with DecisionLedger(db, TENANT_A) as ledger:
            ledger.record(self._decision())
        with self.assertRaises(TenantMismatch):
            DecisionLedger(db, tenant=TENANT_B)

    def test_cross_tenant_decision_is_refused(self):
        with DecisionLedger(self.dir / "ledger.sqlite3", TENANT_A) as ledger:
            with self.assertRaises(CrossTenantWrite):
                ledger.record(self._decision(tenant=TENANT_B))

    def test_export_returns_the_whole_record(self):
        with DecisionLedger(self.dir / "ledger.sqlite3", TENANT_A) as ledger:
            ledger.record(self._decision())
            export = ledger.export()
        self.assertEqual(export["tenant"], TENANT_A)
        self.assertEqual(len(export["decisions"]), 1)


if __name__ == "__main__":
    unittest.main()
