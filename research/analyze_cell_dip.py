import json
from pathlib import Path

def main():
    codegen_path = Path("/tmp/tinker-400-codegen/results.json")
    if not codegen_path.exists():
        print("Codegen results.json not found on this machine.")
        return
    
    codegen_res = json.load(codegen_path.open())
    cell_items = [i for i in codegen_res["items"] if i["type"].startswith("Cell")]
    cell_fails = [i for i in cell_items if not i.get("pass")]

    print(f"Total cell tasks: {len(cell_items)}, Failed: {len(cell_fails)}, Passed: {len(cell_items)-len(cell_fails)}")

    error_types = {}
    trace_dir = Path("/tmp/tinker-400-codegen/traces")

    for f in cell_fails:
        tid = f["id"]
        tpath = trace_dir / f"{tid}.jsonl"
        if not tpath.exists():
            continue
        traces = [json.loads(l) for l in tpath.read_text().splitlines() if l.strip()]
        errors = [t.get("error") for t in traces if t.get("error")]
        last_trace = traces[-1] if traces else {}
        resp = last_trace.get("response") or ""
        
        if any("SyntaxError" in str(e) or "NameError" in str(e) or "AttributeError" in str(e) or "KeyError" in str(e) or "IndexError" in str(e) or "TypeError" in str(e) for e in errors):
            cat = "python_execution_exception"
        elif any("Timeout" in str(e) or "timed out" in str(e) for e in errors):
            cat = "execution_timeout"
        elif "```python" in resp or "import openpyxl" in resp:
            cat = "codegen_logic_wrong_cells"
        elif "{\"cells\":" in resp:
            cat = "values_logic_wrong_cells"
        else:
            cat = "other_error"
        
        error_types[cat] = error_types.get(cat, 0) + 1

    print("\nCell-level Failure Breakdown in Codegen Run:")
    for k, v in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:<35}: {v:>3}")

    print("\nSample Failing Cell Tasks in Codegen Run:")
    for f in cell_fails[:10]:
        tid = f["id"]
        tpath = trace_dir / f"{tid}.jsonl"
        traces = [json.loads(l) for l in tpath.read_text().splitlines() if l.strip()] if tpath.exists() else []
        errs = [str(t.get("error"))[:100] for t in traces if t.get("error")]
        first_resp = traces[0].get("response", "") if traces else ""
        first_resp_type = "python" if ("```python" in first_resp or "openpyxl" in first_resp) else "values"
        print(f"[{tid}] ({f['correct']}/{f['cells']} cells) -> Attempts: {len(traces)}, Mode: {first_resp_type}, Errors: {errs[:2]}")

if __name__ == "__main__":
    main()
