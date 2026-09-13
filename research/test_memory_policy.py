import copy
import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

policy = importlib.import_module("memory_policy")


def record(narrative="EXAMPLE SERVICES", row=2, workbook="a" * 64, **scope):
    return {
        "record_id": f"{workbook}:{row}",
        "scope": {"tenant": "tenant-a", "entity": "entity-a", "account": "account-a", "currency": "EUR", **scope},
        "narrative": narrative,
        "vendor_hint": "",
        "source": {"workbook_sha256": workbook, "sheet": "Transactions", "cell": f"E{row}"},
    }


def correction(narrative="EXAMPLE SERVICES", vendor="Example Services Ltd", **scope):
    return {
        "correction_id": "correction-1",
        "record": record(narrative, **scope),
        "vendor": vendor,
        "reviewer": "controller",
        "rationale": "Explicit synthetic reference-master confirmation",
    }


def replay_cases(candidate):
    alias, scope = candidate["alias"], candidate["scope"]
    positive = record(alias.upper().replace(" ", "   "), 2, "b" * 64, **scope)
    negative = record(alias + " HOLDINGS", 3, "b" * 64, **scope)
    conflict = record(alias, 4, "b" * 64, **scope)
    conflict["vendor_hint"] = "Conflicting vendor"
    cases = [
        {"case_id": "positive", "record": positive, "expected_vendor": candidate["vendor"]},
        {"case_id": "negative", "record": negative, "expected_vendor": None},
        {"case_id": "conflict", "record": conflict, "expected_vendor": None},
    ]
    for row, key in enumerate(policy.SCOPE_FIELDS, 5):
        changed_scope = {**scope, key: scope[key] + "-other"}
        cases.append({"case_id": key, "record": record(alias, row, "b" * 64, **changed_scope), "expected_vendor": None})
    return cases


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.rule = policy.candidate_from_correction(correction(), "rule-1")

    def test_exact_alias_normalizes_only_case_and_whitespace(self):
        self.assertEqual(policy.resolve(record("  Example   SERVICES "), [self.rule])["vendor"], "Example Services Ltd")
        for alias in ("EXAMPLE-SERVICES", "EXAMPLE SERVICES HOLDINGS", "EXAMPLE SERVICE", "EXAMPLE"):
            self.assertIsNone(policy.resolve(record(alias), [self.rule])["vendor"])

    def test_scope_boundaries_and_missing_scope(self):
        for key in policy.SCOPE_FIELDS:
            self.assertIsNone(policy.resolve(record(**{key: "other"}), [self.rule])["vendor"])
        bad = record()
        bad["scope"].pop("tenant")
        with self.assertRaises(ValueError):
            policy.resolve(bad, [self.rule])

    def test_conflicting_evidence_and_rules_abstain(self):
        item = record()
        item["vendor_hint"] = "Other vendor"
        self.assertEqual(policy.resolve(item, [self.rule])["reason"], "conflicting vendor evidence")
        rival = {**self.rule, "rule_id": "rule-2", "vendor": "Other vendor"}
        self.assertEqual(policy.resolve(record(), [self.rule, rival])["reason"], "conflicting approved rules")

    def test_replay_requires_all_coverage_and_actual_improvement(self):
        cases = replay_cases(self.rule)
        report = policy.replay(self.rule, cases, [])
        self.assertTrue(report["eligible"])
        self.assertEqual(report["cases"], 7)
        self.assertEqual(report["improved"], 1)
        self.assertEqual(report["incorrect"], 0)
        self.assertEqual(report["regressions"], 0)
        for missing in ("positive", "negative", "conflict", *policy.SCOPE_FIELDS):
            reduced = [case for case in cases if case["case_id"] != missing]
            self.assertFalse(policy.replay(self.rule, reduced, [])["eligible"])
        no_boundaries = cases[:3]
        self.assertFalse(policy.replay(self.rule, no_boundaries, [])["eligible"])
        incumbent = {**self.rule, "rule_id": "incumbent"}
        self.assertFalse(policy.replay(self.rule, cases, [incumbent])["eligible"])

    def test_replay_rejects_wrong_labels_and_collision(self):
        cases = replay_cases(self.rule)
        cases[0]["expected_vendor"] = "Wrong vendor"
        report = policy.replay(self.rule, cases, [])
        self.assertFalse(report["eligible"])
        self.assertEqual(report["incorrect"], 1)
        rival = {**self.rule, "rule_id": "rival", "vendor": "Other vendor"}
        self.assertFalse(policy.replay(self.rule, replay_cases(self.rule), [rival])["eligible"])

    def test_replay_rejects_training_source_duplicates_and_missing_labels(self):
        for mutation in ("source", "id", "cell", "label"):
            cases = replay_cases(self.rule)
            if mutation == "source":
                cases[0]["record"]["source"]["workbook_sha256"] = "a" * 64
            elif mutation == "id":
                cases[1]["case_id"] = cases[0]["case_id"]
            elif mutation == "cell":
                cases[1]["record"]["source"] = copy.deepcopy(cases[0]["record"]["source"])
            else:
                del cases[0]["expected_vendor"]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                policy.replay(self.rule, cases, [])

    def test_provenance_and_digest(self):
        self.assertEqual(self.rule["reviewer"], "controller")
        self.assertEqual(self.rule["source"], record()["source"])
        changed = {**self.rule, "vendor": "Other"}
        self.assertNotEqual(policy.fingerprint(self.rule), policy.fingerprint(changed))
        bad = correction()
        bad["reviewer"] = " "
        with self.assertRaises(ValueError):
            policy.candidate_from_correction(bad, "rule-2")


if __name__ == "__main__":
    unittest.main()
