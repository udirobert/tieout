#!/usr/bin/env bash
# Offline Syndicate demo — exception queue without Tinker (for video / CI).
# Simulates agent output using golden workbooks, then builds exceptions.json.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ROOT}/demo/close-tieout"
OUT="${2:-/tmp/syndicate-demo}"
ID="${1:-close-tieout-bank-cp}"
MODE="${3:-golden}"  # golden | init (agent failed / partial)

if [[ ! -f "${DATA}/dataset.json" ]]; then
  echo "Run: python demo/build_fixtures.py"
  exit 1
fi

mkdir -p "${OUT}/outputs" "${OUT}/exceptions"

cd "${ROOT}/research"
uv run python <<PY
import json, shutil, sys
from pathlib import Path

ROOT = Path("${ROOT}")
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "harness"))

from sb import load_dataset, answer_cells
from exceptions import write_exceptions
from parsing import cell_ref
import openpyxl

data = ROOT / "demo/close-tieout"
out_dir = Path("${OUT}")
tid = "${ID}"
mode = "${MODE}"

tasks = {t["id"]: t for t in load_dataset(data)}
t = tasks[tid]
src = t["init_xlsx"] if mode == "init" else t["golden_xlsx"]
out = out_dir / "outputs" / f"{tid}.xlsx"
shutil.copy(src, out)

written = {}
wb = openpyxl.load_workbook(out, data_only=True)
for sheet, coord in answer_cells(t, wb):
    ws = wb[sheet] if sheet in wb.sheetnames else wb.active
    written[cell_ref(sheet or ws.title, coord)] = ws[coord].value
wb.close()

status = "partial: simulated init" if mode == "init" else "ok: simulated golden"
payload = write_exceptions(out_dir, t, status, "offline demo", {"written": written}, out)

print(f"=== simulate_demo: {tid} ({mode}) ===")
print(f"Output:     {out}")
print(f"Exceptions: {len(payload['exceptions'])}")
print(f"Queue:      {out_dir / 'exceptions.json'}")
print()
for exc in payload["exceptions"][:5]:
    print(f"  {exc['cell']} | {exc['reason']} | proposed={exc['proposed_value']!r}")
    for ev in exc["evidence_rows"][:2]:
        print(f"    evidence: {ev['sheet']} row {ev['row']} key={ev['key']!r}")
if len(payload["exceptions"]) > 5:
    print(f"  ... +{len(payload['exceptions']) - 5} more")
print()
print("Human review (interactive):")
print(f"  cd research && uv run python ../harness/exceptions.py review {out_dir}/exceptions.json")
print("Human review (approve all — demo shortcut):")
print(f"  cd research && uv run python ../harness/exceptions.py review {out_dir}/exceptions.json --approve-all")
PY
