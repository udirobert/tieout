"""H-MEM engine seam in the governed memory store.

The store is exercised against a duck-typed fake — the contract being tested
is which engine calls the lifecycle makes and what happens when they fail,
not the engine itself (that is what the conformance suite is for).
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "harness"))

hmem_client = importlib.import_module("hmem_client")
memory_store = importlib.import_module("memory_store")
tenant = importlib.import_module("tenant")
test_memory_policy = importlib.import_module("test_memory_policy")

HmemUnavailable = hmem_client.HmemUnavailable
MemoryStore = memory_store.MemoryStore
correction = test_memory_policy.correction
record = test_memory_policy.record
replay_cases = test_memory_policy.replay_cases


class FakeEngine:
    """Records the calls the lifecycle makes; `fail` simulates the sidecar down."""

    def __init__(self, tenant="tenant-a"):
        self.tenant = tenant
        self.seq = 0
        self.adds = []
        self.promoted = []
        self.superseded = []
        self.queries = []
        self.fail = False

    def _maybe_fail(self):
        if self.fail:
            raise HmemUnavailable("engine offline")

    def add(self, **fields):
        self._maybe_fail()
        self.seq += 1
        self.adds.append(fields)
        return {"id": f"mem-{self.seq}"}

    def promote(self, memory_id, layer):
        self._maybe_fail()
        self.promoted.append((memory_id, layer))

    def supersede(self, memory_id, by):
        self._maybe_fail()
        self.superseded.append((memory_id, by))

    def query(self, query, **_opts):
        self._maybe_fail()
        self.queries.append(query)
        return {
            "memories": [
                {
                    "memory": {
                        "id": "mem-1",
                        "content": "prior correction",
                        "layer": "long_term",
                    },
                    "relevance": 0.9,
                }
            ],
            "context": "",
            "trace": {},
        }


class EngineSeamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "memory.sqlite3"
        self.engine = FakeEngine()
        self.store = MemoryStore(self.db, hmem=self.engine)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _activate(self):
        payload = {k: v for k, v in correction().items() if k != "correction_id"}
        approved = self.store.record_correction(**payload)
        rule = self.store.propose(approved["correction_id"])
        self.store.validate(rule["rule_id"], replay_cases(rule), "controller")
        self.store.activate(rule["rule_id"], "controller")
        return rule

    def test_correction_and_proposal_write_engine_memories(self):
        payload = {k: v for k, v in correction().items() if k != "correction_id"}
        approved = self.store.record_correction(**payload)
        self.assertEqual(len(self.engine.adds), 1)
        self.assertEqual(self.engine.adds[0]["source"], "user_correction")
        rule = self.store.propose(approved["correction_id"])
        self.assertEqual(len(self.engine.adds), 2)
        self.assertEqual(self.engine.adds[1]["derivedFrom"], ["mem-1"])
        self.assertIsNotNone(rule)

    def test_activate_promotes_and_revoke_supersedes(self):
        rule = self._activate()
        self.assertEqual(self.engine.promoted, [("mem-2", "long_term")])
        self.store.revoke(rule["rule_id"], "controller", "rollback")
        self.assertEqual(self.engine.superseded, [("mem-2", "revoked")])

    def test_suggest_attaches_recall(self):
        # A write first: the engine is only used once the store is bound to a
        # tenant — an unbound store has no tenant to trust, so recall is skipped.
        payload = {k: v for k, v in correction().items() if k != "correction_id"}
        self.store.record_correction(**payload)
        suggestion = self.store.suggest([record()])[0]
        self.assertEqual(suggestion["decision"], "review")
        self.assertEqual(len(self.engine.queries), 1)
        self.assertEqual(suggestion["recall"][0]["memory_id"], "mem-1")
        self.assertEqual(suggestion["recall"][0]["score"], 0.9)

    def test_unbound_store_skips_recall(self):
        suggestion = self.store.suggest([record()])[0]
        self.assertNotIn("recall", suggestion)
        self.assertEqual(self.engine.queries, [])

    def test_engine_down_degrades_everything(self):
        self.engine.fail = True
        rule = self._activate()
        self.store.revoke(rule["rule_id"], "controller", "rollback")
        self.assertEqual(self.store.rules()[0]["status"], "revoked")
        suggestion = self.store.suggest([record()])[0]
        self.assertNotIn("recall", suggestion)
        self.assertEqual(self.engine.promoted, [])
        self.assertEqual(self.engine.superseded, [])

    def test_no_engine_is_plain_store(self):
        self.store.close()
        store = MemoryStore(self.db)
        try:
            suggestion = store.suggest([record()])[0]
        finally:
            store.close()
        self.assertNotIn("recall", suggestion)

    def test_cross_tenant_engine_refused(self):
        self.store.close()
        store = MemoryStore(self.db, tenant="tenant-a", hmem=FakeEngine("tenant-b"))
        try:
            with self.assertRaises(tenant.CrossTenantWrite):
                store.suggest([record()])
            payload = {k: v for k, v in correction().items() if k != "correction_id"}
            with self.assertRaises(tenant.CrossTenantWrite):
                store.record_correction(**payload)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
