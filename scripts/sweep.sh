#!/bin/bash
# Config sweep — model × path on a task subsample (factorial, not one-at-a-time).
#
#   ./scripts/sweep.sh research/data/spreadsheetbench_verified_400 15
#   ./scripts/sweep.sh demo/close-tieout 3 /tmp/tieout-sweep
#
# Env overrides: MODELS="wandb:... wandb:..." PATHS="hybrid values"
# Requires WANDB_API_KEY (or whatever keys the chosen adapters need).
set -uo pipefail
cd "$(dirname "$0")/.."

DATASET="${1:?usage: sweep.sh <dataset-dir> [N] [out-dir]}"
N="${2:-15}"
OUT="${3:-/tmp/tieout-sweep}"
MODELS="${MODELS:-wandb:meta-llama/Llama-3.3-70B-Instruct wandb:Qwen/Qwen3.8-27B wandb:deepseek-ai/DeepSeek-V4-Flash-0731}"
PATHS="${PATHS:-hybrid values}"

PY="research/.venv/bin/python"
[ -x "$PY" ] || PY="uv --directory research run python"

IDS=$($PY -c "import json;print(','.join(str(t['id']) for t in json.load(open('$DATASET/dataset.json'))[:$N]))")
echo "sweep: $N task(s) | models: $MODELS | paths: $PATHS"

RECALC="--no-recalc"
command -v soffice >/dev/null 2>&1 && RECALC=""

printf "%-46s %-8s %s\n" model path cell_accuracy
for model in $MODELS; do
  for path in $PATHS; do
    tag=$(echo "$model" | tr '/:' '__')-$path
    dir="$OUT/$tag"
    $PY harness/pipeline.py --dataset-dir "$DATASET" --out-dir "$dir" \
      --ids "$IDS" --model "$model" --path "$path" --fresh >/dev/null 2>&1
    acc=$($PY research/evaluate.py --predictions "$dir/predictions.jsonl" \
      --dataset-dir "$DATASET" $RECALC --out "$dir/score.json" --quiet 2>/dev/null; \
      $PY -c "import json;print(json.load(open('$dir/score.json'))['summary']['cell_accuracy'])" 2>/dev/null)
    printf "%-46s %-8s %s\n" "$model" "$path" "${acc:-eval-failed}"
  done
done
echo "outputs under $OUT/"
