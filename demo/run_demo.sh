#!/usr/bin/env bash
# Syndicate demo — one finance-close scenario (no Tinker call unless TINKER_API_KEY set).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ROOT}/demo/close-tieout"
OUT="${TMPDIR:-/tmp}/syndicate-demo"
ID="${1:-close-tieout-movements-rec}"

if [[ ! -f "${DATA}/dataset.json" ]]; then
  echo "Fixtures missing. Run: python demo/build_fixtures.py"
  exit 1
fi

echo "=== tieout Syndicate demo: ${ID} ==="
echo "Dataset: ${DATA}"
echo "Output:  ${OUT}"
echo ""
echo "Dry run (no API — shows fixture layout):"
python3 -c "
import json
from pathlib import Path
tasks = json.loads(Path('${DATA}/dataset.json').read_text())
t = next(x for x in tasks if x['id']=='${ID}')
print('Instruction:', t['instruction'][:200], '...')
print('Answer:', t['answer_sheet'], t['answer_position'])
"

if [[ -z "${TINKER_API_KEY:-}" ]]; then
  echo ""
  echo "TINKER_API_KEY not set — skipping live agent run."
  echo "Set key and re-run to execute pipeline:"
  echo "  python harness/pipeline.py --dataset-dir ${DATA} --out-dir ${OUT} --ids ${ID} --path hybrid --fresh"
  exit 0
fi

cd "${ROOT}"
python harness/pipeline.py \
  --dataset-dir "${DATA}" \
  --out-dir "${OUT}" \
  --ids "${ID}" \
  --path hybrid \
  --fresh

echo ""
echo "Trace: ${OUT}/traces/${ID}.jsonl"
echo "Output workbook: ${OUT}/outputs/${ID}.xlsx"
