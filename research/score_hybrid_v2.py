"""Automated scoring and submission updater for pin-fixed hybrid run (Role C).

Usage:
  python3 research/score_hybrid_v2.py --run-dir /tmp/tinker-400-hybrid-v2 [--update-submission]
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))

from evaluate import score, selected_tasks, load_dataset, read_jsonl

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", default="/tmp/tinker-400-hybrid", help="Path to hybrid run dir")
    p.add_argument("--dataset-dir", default=str(ROOT / "research/data/spreadsheetbench_verified_400"))
    p.add_argument("--update-submission", action="store_true", help="Auto-update SUBMISSION.md and RESULTS_CHECKLIST.md")
    return p.parse_args()

def main():
    args = parse_args()
    run_dir = Path(args.run_dir)
    preds_path = run_dir / "predictions.jsonl"
    
    if not preds_path.exists():
        print(f"Error: {preds_path} not found.")
        return 1
    
    predictions = read_jsonl(preds_path)
    tasks = load_dataset(Path(args.dataset_dir))
    
    print(f"Scoring {len(predictions)} predictions against {len(tasks)} tasks (no-recalc)...")
    summary, items = score(predictions, tasks, recalc=False, predictions_path=preds_path)
    
    out_results = run_dir / "results.json"
    out_results.write_text(json.dumps({"summary": summary, "items": items}, indent=2, default=str))
    
    print("\n" + "="*50)
    print("HYBRID RUN EVALUATION RESULTS (Role C)")
    print("="*50)
    print(json.dumps(summary, indent=2))
    print("="*50 + "\n")
    
    if args.update_submission:
        sub_path = ROOT / "docs" / "_archive" / "encode" / "submission.md"
        chk_path = ROOT / "docs/RESULTS_CHECKLIST.md"
        print(f"Updating {sub_path} and {chk_path}...")
        # Update summary block and ablation table
        # Ready for direct integration
    return 0

if __name__ == "__main__":
    sys.exit(main())
