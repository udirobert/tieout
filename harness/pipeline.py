"""tieout pipeline — entry point for container + local runs.

Contract (matches research/SUBMISSION.md + baseline/common.py):
  python harness/pipeline.py --dataset-dir /data --out-dir /out [--ids 13-1,51-12] [--model ...] [--concurrency 4]

Writes to out-dir: predictions.jsonl, outputs/<id>.xlsx, traces/<id>.jsonl, run.log
- One line per task in predictions.jsonl: {"id","output":"outputs/<id>.xlsx","status":"ok|error..."}
- Missing line / missing file / unreadable file = 0. On failure copy init workbook, keep error.
- Keys via env only (OPENROUTER_API_KEY / TINKER_API_KEY). Model ids fixed, temperature 0.

Loop per task (v0 values, v1 formulas/code-exec):
  1. classify (prompts.classify) -> build prompt (values-first)
  2. complete() -> parse JSON cells -> write_output (copy init, write graded cells only)
  3. verifier second-derivation check -> retry <=3 (verifier.MAX_ATTEMPTS)
  4. executor path (agentic): model writes openpyxl snippet -> executor.run_snippet
     INSIDE container -> verifier -> retry

Venue: implement complete() for OpenRouter (llm_predict.py pattern) and Tinker
(tinker_predict.py pattern, --base-model Qwen/Qwen3-8B, --model-path tinker://...).
Sampling nondeterminism (+-few tasks) is expected.
"""

import argparse
import asyncio

# Venue: sys.path insert for research/sb.py + harness modules; imports below resolve there.
# from sb import load_dataset, answer_cells
# from harness.prompts import classify, build_values_prompt
# from harness.tracer import MAX_WORKBOOK_CHARS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--ids", help="comma-separated task ids (default: all)")
    p.add_argument("--model", default="qwen3-8-27b")
    p.add_argument("--concurrency", type=int, default=4)
    return p.parse_args()


async def main() -> None:
    raise NotImplementedError(
        "implement: complete() per harness/README.md (values-first v0)"
    )


if __name__ == "__main__":
    asyncio.run(main())
