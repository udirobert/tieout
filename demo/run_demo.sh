#!/usr/bin/env bash
# Syndicate demo — live Tinker run or offline simulate.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${ROOT}/demo/close-tieout"
OUT="${TMPDIR:-/tmp}/syndicate-demo"
ID="${1:-close-tieout-bank-cp}"
SIMULATE="${SIMULATE:-0}"

if [[ ! -f "${DATA}/dataset.json" ]]; then
  echo "Fixtures missing. Run: python demo/build_fixtures.py"
  exit 1
fi

echo "=== tieout Syndicate demo: ${ID} ==="
echo "Dataset: ${DATA}"
echo "Output:  ${OUT}"
echo ""

if [[ "${SIMULATE}" == "1" ]] || [[ -z "${TINKER_API_KEY:-}" ]]; then
  if [[ -z "${TINKER_API_KEY:-}" ]]; then
    echo "TINKER_API_KEY not set — running offline simulate (golden output + exception queue)."
  else
    echo "SIMULATE=1 — offline mode."
  fi
  exec "${ROOT}/demo/simulate_demo.sh" "${ID}" "${OUT}" golden
fi

cd "${ROOT}/research"
uv run python ../harness/pipeline.py \
  --dataset-dir "${DATA}" \
  --out-dir "${OUT}" \
  --ids "${ID}" \
  --path hybrid \
  --fresh

echo ""
echo "Trace:      ${OUT}/traces/${ID}.jsonl"
echo "Output:     ${OUT}/outputs/${ID}.xlsx"
echo "Exceptions: ${OUT}/exceptions.json"
echo "Review:     cd research && uv run python ../harness/exceptions.py review ${OUT}/exceptions.json"
