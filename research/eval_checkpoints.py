"""Automated checkpoint evaluation runner and progress logger (Role C).

Evaluates any checkpoint against SpreadsheetBench Verified 400 using the
locked standard evaluation rig (--all --no-recalc), producing results.json
and formatted ablation rows.

Usage:
  # Score an existing predictions file:
  python3 research/eval_checkpoints.py --predictions /tmp/tinker-400-lora-v2/predictions.jsonl --name "LoRA v2 (step 400)"

  # Run inference + scoring loop for a Tinker checkpoint:
  python3 research/eval_checkpoints.py --model-path tinker://<run-id>/sampler_weights/000400 --name "LoRA v2 (400 steps)"
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT))

from evaluate import score, load_dataset, read_jsonl

DEFAULT_DATASET = ROOT / "research/data/spreadsheetbench_verified_400"

def parse_args():
    p = argparse.ArgumentParser(description="Evaluate checkpoints on SpreadsheetBench Verified 400.")
    p.add_argument("--predictions", help="Existing predictions.jsonl to score")
    p.add_argument("--model-path", help="Tinker checkpoint path (tinker://...)")
    p.add_argument("--base-model", default="Qwen/Qwen3.8-27B", help="Base model for tokenizer/sampler")
    p.add_argument("--out-dir", help="Directory to store outputs/traces/predictions")
    p.add_argument("--dataset-dir", default=str(DEFAULT_DATASET), help="Dataset root")
    p.add_argument("--name", default="Checkpoint Eval", help="Label for ablation table row")
    p.add_argument("--concurrency", type=int, default=8, help="Inference concurrency")
    p.add_argument("--recalc", action="store_true", help="Enable LibreOffice recalculation (default: False)")
    return p.parse_args()

def run_inference(args, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(ROOT / "harness/pipeline.py"),
        "--dataset-dir", args.dataset_dir,
        "--out-dir", str(out_dir),
        "--model", f"tinker:{args.base_model}|{args.model_path}",
        "--concurrency", str(args.concurrency),
    ]
    print(f"Launching inference: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    args = parse_args()
    dataset_path = Path(args.dataset_dir)
    
    if args.predictions:
        preds_path = Path(args.predictions)
        out_dir = preds_path.parent
    elif args.model_path:
        ckpt_name = args.model_path.split("/")[-1].replace(":", "_")
        out_dir = Path(args.out_dir) if args.out_dir else Path(f"/tmp/eval-ckpt-{ckpt_name}")
        preds_path = out_dir / "predictions.jsonl"
        run_inference(args, out_dir)
    else:
        print("Error: Specify either --predictions or --model-path")
        return 1

    predictions = read_jsonl(preds_path)
    tasks = load_dataset(dataset_path)
    
    print(f"\nScoring {len(predictions)} predictions against {len(tasks)} tasks (--all, recalc={args.recalc})...")
    summary, items = score(predictions, tasks, recalc=args.recalc, predictions_path=preds_path)
    
    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps({"summary": summary, "items": items}, indent=2, default=str))
    
    print("\n" + "="*70)
    print(f"EVALUATION SUMMARY: {args.name}")
    print("="*70)
    print(json.dumps(summary, indent=2))
    print("="*70)
    
    pass_rate = summary.get("pass_rate", 0)
    cell_acc = summary.get("cell_accuracy", 0)
    cell_pass = summary.get("pass_rate_cell_level", 0)
    sheet_pass = summary.get("pass_rate_sheet_level", 0)
    
    md_row = (
        f"| *+ {args.name}* | **{pass_rate*100:.2f}%** ({int(pass_rate*400)}/400) | "
        f"**{cell_acc*100:.2f}%** | **{cell_pass*100:.2f}%** ({int(cell_pass*275)}/275) | "
        f"**{sheet_pass*100:.2f}%** ({int(sheet_pass*125)}/125) | `{out_dir}` |"
    )
    print("\nFormatted Ablation Table Row (ready for SUBMISSION.md):")
    print(md_row)
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
