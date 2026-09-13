from __future__ import annotations

import hashlib
import json
from typing import Any

SCOPE_FIELDS = ("tenant", "entity", "account", "currency")
POLICY_VERSION = "exact-alias-v1"


def required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def scope_of(value: dict) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValueError("scope must be an object")
    return {key: required_text(value.get(key), key) for key in SCOPE_FIELDS}


def alias_key(value: str) -> str:
    return " ".join(required_text(value, "narrative").casefold().split())


def fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def checked_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    source = record.get("source")
    if not isinstance(source, dict):
        raise ValueError("source must be an object")
    digest = required_text(source.get("workbook_sha256"), "workbook_sha256")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("workbook_sha256 must be a lowercase SHA-256 digest")
    hint = record.get("vendor_hint", "")
    if not isinstance(hint, str):
        raise ValueError("vendor_hint must be a string")
    return {
        "record_id": required_text(record.get("record_id"), "record_id"),
        "scope": scope_of(record.get("scope")),
        "narrative": required_text(record.get("narrative"), "narrative"),
        "vendor_hint": hint.strip(),
        "source": {
            "workbook_sha256": digest,
            "sheet": required_text(source.get("sheet"), "sheet"),
            "cell": required_text(source.get("cell"), "cell"),
        },
    }


def candidate_from_correction(correction: dict, rule_id: str) -> dict:
    record = checked_record(correction["record"])
    return {
        "rule_id": required_text(rule_id, "rule_id"),
        "version": 1,
        "policy_version": POLICY_VERSION,
        "scope": record["scope"],
        "alias": alias_key(record["narrative"]),
        "vendor": required_text(correction.get("vendor"), "vendor"),
        "correction_id": required_text(correction.get("correction_id"), "correction_id"),
        "source": record["source"],
        "reviewer": required_text(correction.get("reviewer"), "reviewer"),
        "rationale": required_text(correction.get("rationale"), "rationale"),
    }


def resolve(record: dict, active_rules: list[dict]) -> dict:
    record = checked_record(record)
    applicable = [
        rule for rule in active_rules
        if rule["policy_version"] == POLICY_VERSION
        and rule["scope"] == record["scope"]
        and rule["alias"] == alias_key(record["narrative"])
    ]
    rule_ids = sorted(rule["rule_id"] for rule in applicable)
    vendors = {rule["vendor"] for rule in applicable}
    if not vendors:
        return {"decision": "review", "vendor": None, "reason": "no approved exact alias", "rule_ids": []}
    if len(vendors) != 1:
        return {"decision": "review", "vendor": None, "reason": "conflicting approved rules", "rule_ids": rule_ids}
    vendor = next(iter(vendors))
    if record["vendor_hint"] and record["vendor_hint"] != vendor:
        return {"decision": "review", "vendor": None, "reason": "conflicting vendor evidence", "rule_ids": rule_ids}
    return {"decision": "suggested", "vendor": vendor, "reason": "approved exact alias", "rule_ids": rule_ids}


def replay(candidate: dict, cases: list[dict], active_rules: list[dict]) -> dict:
    if not isinstance(cases, list) or not cases:
        raise ValueError("replay requires labeled cases")
    ids = set()
    source_ids = set()
    results = []
    coverage = {"positive": False, "hard_negative": False, "scope_boundary": False, "conflict": False}
    boundaries = {key: False for key in SCOPE_FIELDS}
    improved = regressions = incorrect = 0
    for case in cases:
        case_id = required_text(case.get("case_id"), "case_id")
        if case_id in ids:
            raise ValueError("duplicate replay case_id")
        ids.add(case_id)
        record = checked_record(case["record"])
        source_id = fingerprint(record["source"])
        if source_id in source_ids:
            raise ValueError("duplicate replay source cell")
        source_ids.add(source_id)
        if record["source"]["workbook_sha256"] == candidate["source"]["workbook_sha256"]:
            raise ValueError("replay must not reuse the correction workbook")
        if "expected_vendor" not in case:
            raise ValueError("replay case needs expected_vendor, null means review")
        expected = case["expected_vendor"]
        if expected is not None:
            expected = required_text(expected, "expected_vendor")
        before = resolve(record, active_rules)
        after = resolve(record, [*active_rules, candidate])
        before_ok, after_ok = before["vendor"] == expected, after["vendor"] == expected
        improved += int(after_ok and not before_ok)
        regressions += int(before_ok and not after_ok)
        incorrect += int(not after_ok)
        same_scope = record["scope"] == candidate["scope"]
        same_alias = alias_key(record["narrative"]) == candidate["alias"]
        coverage["positive"] |= same_scope and same_alias and expected == candidate["vendor"] and after_ok
        coverage["hard_negative"] |= same_scope and not same_alias and expected is None and after_ok
        changed_scope = [key for key in SCOPE_FIELDS if record["scope"][key] != candidate["scope"][key]]
        if len(changed_scope) == 1 and same_alias and expected is None and after_ok:
            boundaries[changed_scope[0]] = True
        coverage["scope_boundary"] = all(boundaries.values())
        coverage["conflict"] |= same_scope and same_alias and bool(record["vendor_hint"]) and record["vendor_hint"] != candidate["vendor"] and expected is None and after_ok
        results.append({"case_id": case_id, "source": record["source"], "expected_vendor": expected, "before": before, "after": after, "passed": after_ok})
    collision = any(
        rule["scope"] == candidate["scope"] and rule["alias"] == candidate["alias"] and rule["vendor"] != candidate["vendor"]
        for rule in active_rules
    )
    return {
        "policy_version": POLICY_VERSION,
        "candidate_digest": fingerprint(candidate),
        "cases_digest": fingerprint(cases),
        "active_rules_digest": fingerprint(active_rules),
        "cases": len(cases),
        "improved": improved,
        "regressions": regressions,
        "incorrect": incorrect,
        "coverage": coverage,
        "scope_boundaries": boundaries,
        "conflicting_rule": collision,
        "eligible": all(coverage.values()) and improved > 0 and regressions == 0 and incorrect == 0 and not collision,
        "results": results,
    }
