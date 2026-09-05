"""Trace analyzer and failure taxonomy tool for tieout evaluation runs (Role C).

Usage:
  python3 research/analyze_traces.py --run-dir /tmp/tinker-400
"""

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Analyze run predictions, traces, and failure taxonomies.")
    p.add_argument("--run-dir", required=True, help="Directory containing predictions.jsonl and traces/")
    return p.parse_args()


def load_jsonl(path: Path):
    if not path.exists():
        return []
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except Exception:
                    pass
    return items


def classify_trace_failure(trace_records, pred_status):
    """Categorize reason for failure based on trace records and predictions status."""
    if not trace_records:
        return "no_trace"
    
    last_trace = trace_records[-1]
    last_resp = last_trace.get("response") or ""
    error = last_trace.get("error") or ""

    if "missing answer cells" in pred_status or "missing answer cells" in error:
        return "missing_answer_cells"
    if "non-scalar" in pred_status or "non-scalar" in error:
        return "non_scalar_values"
    if "no JSON object" in error or "JSONDecodeError" in error:
        if len(last_resp) > 15000:
            return "json_truncation_or_overflow"
        return "json_format_malformed"
    if "<think>" in last_resp:
        return "thinking_tag_leak"
    if "error" in pred_status or error:
        return "call_or_runtime_exception"
    if pred_status.startswith("partial"):
        return "partial_unverified"
    return "unknown"


def main():
    args = parse_args()
    run_dir = Path(args.run_dir)
    preds_file = run_dir / "predictions.jsonl"
    traces_dir = run_dir / "traces"

    predictions = load_jsonl(preds_file)
    print(f"==================================================")
    print(f"TIEOUT RUN ANALYSIS & FAILURE TAXONOMY (Role C)")
    print(f"Run Directory: {run_dir}")
    print(f"Total Predictions: {len(predictions)}")
    print(f"==================================================")

    if not predictions:
        print("No predictions found in directory.")
        return

    status_counts = Counter(p.get("status", "unknown").split(":")[0] for p in predictions)
    print("\n--- High-level Status Counts ---")
    for st, count in status_counts.most_common():
        pct = (count / len(predictions)) * 100
        print(f"  {st:<15}: {count:>4} ({pct:>5.1f}%)")

    latencies = []
    input_tokens = []
    output_tokens = []
    attempts_per_task = []
    failure_taxonomies = Counter()
    non_ok_details = []

    for pred in predictions:
        task_id = pred["id"]
        trace_file = traces_dir / f"{task_id}.jsonl"
        traces = load_jsonl(trace_file) if trace_file.exists() else []
        attempts_per_task.append(len(traces) if traces else 1)

        for t in traces:
            if t.get("latency_ms"):
                latencies.append(t["latency_ms"])
            if t.get("input_tokens"):
                input_tokens.append(t["input_tokens"])
            if t.get("output_tokens"):
                output_tokens.append(t["output_tokens"])

        status = pred.get("status", "")
        if not status.startswith("ok"):
            cat = classify_trace_failure(traces, status)
            failure_taxonomies[cat] += 1
            non_ok_details.append((task_id, cat, status[:80]))

    print("\n--- Latency & Token Metrics ---")
    if latencies:
        print(f"  Latency (ms) : Mean={int(statistics.mean(latencies))}, P50={int(statistics.median(latencies))}, Max={max(latencies)}")
    if input_tokens:
        print(f"  Input Tokens : Mean={int(statistics.mean(input_tokens))}, Max={max(input_tokens)}")
    if output_tokens:
        print(f"  Output Tokens: Mean={int(statistics.mean(output_tokens))}, Max={max(output_tokens)}")
    if attempts_per_task:
        print(f"  Attempts/Task: Mean={statistics.mean(attempts_per_task):.2f}, Max={max(attempts_per_task)}")

    if failure_taxonomies:
        print("\n--- Failure Taxonomy Breakdown ---")
        for cat, cnt in failure_taxonomies.most_common():
            pct = (cnt / len(predictions)) * 100
            print(f"  {cat:<30}: {cnt:>4} ({pct:>5.1f}%)")

        print("\n--- Sample Non-OK Tasks ---")
        for task_id, cat, detail in non_ok_details[:10]:
            print(f"  [{task_id}] ({cat}) -> {detail}")

    print("\n==================================================")


if __name__ == "__main__":
    main()
