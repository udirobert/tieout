#!/bin/bash
# B — rejection-sampling data generation (full run). Requires Tinker account free
# (i.e. /tmp/tinker-400.log has its "total" line before launch).
set -euo pipefail
cd "$(dirname "$0")/.."
exec research/.venv/bin/python research/sample_data.py \
  --dataset-dir research/data/spreadsheetbench_verified_400 \
  --out-dir research/data/sft \
  --n 8 --concurrency 6 --max-per-task 2 \
  --model tinker:Qwen/Qwen3.8-27B
