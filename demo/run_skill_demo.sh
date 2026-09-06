#!/usr/bin/env bash
# Skill improvement demo — category skill injection for CFO tasks (no inference).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}/research"

uv run python <<PY
import sys
from pathlib import Path

ROOT = Path("${ROOT}")
sys.path.insert(0, str(ROOT / "harness"))

from skills import get_skill_fragment

cases = [
    (
        "close-tieout-le-map",
        "Fill column E (Corvus LE ID) for each legal entity by looking up the matching Corvus LE name in column D.",
    ),
    (
        "close-tieout-bank-cp",
        "Match Pulled Out Sender/Beneficiary to Vendor Master List; leave blank if no match for exception queue.",
    ),
    (
        "close-tieout-movements-rec",
        "Fill Status: OK if Net Movement is zero, otherwise EXCEPTION for controller review.",
    ),
]

print("=== tieout skill improvement loop (no retrain) ===\\n")
print("Before: generic system prompt only")
print("After:  get_skill_fragment(instruction) appends domain guidance\\n")

for task_id, instruction in cases:
    skill = get_skill_fragment(instruction)
    print(f"--- {task_id} ---")
    print(f"Instruction: {instruction[:90]}...")
    if skill:
        print("Skill injected:")
        for line in skill.strip().split("\\n")[:4]:
            print(f"  {line}")
    else:
        print("Skill injected: (none — add from failure trace in docs/TAXONOMY.md)")
    print()

print("Live re-run (TINKER_API_KEY): ./demo/run_demo.sh close-tieout-le-map")
PY
