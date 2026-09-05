"""tieout pipeline — values-first v0. Entry: container + local runs.

  python harness/pipeline.py --dataset-dir /data --out-dir /out [--ids ...] [--model gemini:gemini-3.7-flash]

Writes: predictions.jsonl, outputs/<id>.xlsx, traces/<id>.jsonl, run.log.
Missing line / missing file = 0, so on total failure we copy the init workbook as output.
Per task: serialize (fill-aware) -> complete() -> lenient parse -> write graded cells
(dates coerced) -> sanity verify -> retry <=3 -> best guess, never blank.
"""

import argparse
import asyncio
import datetime
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT))

import openpyxl  # noqa: E402
from sb import answer_cells, load_dataset  # noqa: E402

from adapters import make_completer  # noqa: E402
from parsing import parse_answer  # noqa: E402
from prompts import SYSTEM_VALUES, build_repair_prompt, build_values_prompt  # noqa: E402
from serializer import serialize_task_workbook  # noqa: E402
from tracer import append_trace  # noqa: E402
from verifier import MAX_ATTEMPTS, sanity_check  # noqa: E402

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$")


def _coerce(value, target_ws, coord):
    """ISO strings -> real datetimes when the target cell shows a date format (scorer wants serials)."""
    if isinstance(value, str) and _ISO_DATE.match(value):
        numfmt = target_ws[coord].number_format or ""
        if any(tok in numfmt for tok in ("yy", "dd", "d/", "mm", "h:")) or "T" in value:
            fmt = "%Y-%m-%d %H:%M:%S" if ":" in value else "%Y-%m-%d"
            return datetime.datetime.strptime(value.replace("T", " "), fmt)
    return value


def write_output(task: dict, answer, out_path: Path) -> dict:
    cells = {c.cell: c.value for c in answer.cells}
    shutil.copy(task["init_xlsx"], out_path)
    wb = openpyxl.load_workbook(out_path)
    graded = [(sheet, coord) for sheet, coord in answer_cells(task, wb)]
    written = {}
    for sheet, coord in graded:
        ws = wb[sheet] if sheet and sheet in wb.sheetnames else wb.active
        if coord in cells:
            v = cells[coord]
            v = _coerce(
                "" if v is None else v, ws, coord
            )  # null -> empty cell (scorer: "" == empty)
            ws[coord] = v
            written[coord] = v
    wb.save(out_path)
    return {"graded": [c for _, c in graded], "written": written}


async def predict_task(
    complete, task: dict, out_dir: Path, sem: asyncio.Semaphore
) -> str:
    out = out_dir / "outputs" / f"{task['id']}.xlsx"
    step = 0
    status = "error: no attempt"
    last_reason = ""
    async with sem:
        prompt = build_values_prompt(task, serialize_task_workbook(task))
        wb0 = openpyxl.load_workbook(task["init_xlsx"])
        graded_coords = [c for _, c in answer_cells(task, wb0)]
        last_reply = ""  # kept for the targeted repair prompt (attribution-guided)
        for attempt in range(MAX_ATTEMPTS):
            step += 1
            trace = {
                "step": step,
                "model": complete.model_name,
                "prompt": prompt,
                "response": None,
                "input_tokens": None,
                "output_tokens": None,
                "latency_ms": None,
                "error": None,
                "tool": None,
                "tool_input": None,
                "tool_output": None,
            }
            started = time.time()
            try:
                text, in_tok, out_tok = await complete(prompt, SYSTEM_VALUES)
                trace.update(response=text, input_tokens=in_tok, output_tokens=out_tok)
                answer = parse_answer(text)
                info = write_output(task, answer, out)
                ok, reason = sanity_check(
                    info["graded"], {c: v for c, v in info["written"].items()}
                )
                last_reason = reason
                if ok:
                    trace["latency_ms"] = int((time.time() - started) * 1000)
                    append_trace(out_dir, task["id"], trace)
                    return "ok"
                status = f"partial: {reason}"
                last_reply = text  # attribution: carry the rejected reply into repair
            except Exception as e:  # noqa: BLE001 — best guess, never blank
                status = f"error: {type(e).__name__}: {e}"[:200]
                trace["error"] = status
                last_reply = (trace.get("response") or "")  # may be None on call failure
            trace["latency_ms"] = int((time.time() - started) * 1000)
            append_trace(out_dir, task["id"], trace)
            # Attribution-guided repair (notes §4.2): next attempt gets a targeted
            # "what failed, why, smallest edit" prompt instead of the identical one.
            if attempt + 1 < MAX_ATTEMPTS and last_reply:
                failure = last_reason or status
                prompt = build_repair_prompt(
                    task, last_reply, failure, graded_coords
                )
        if (
            not out.exists()
        ):  # every attempt failed to write — never ship a missing file
            shutil.copy(task["init_xlsx"], out)
        return f"{status} (best guess after {MAX_ATTEMPTS} attempts: {last_reason})"[
            :200
        ]


async def main() -> None:
    args = parse_args()
    for env_path in (ROOT / ".env", ROOT / "research" / ".env"):
        for line in env_path.read_text().splitlines() if env_path.exists() else []:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    out_dir = Path(args.out_dir)
    for sub in ("outputs", "traces"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    (out_dir / "run.log").touch(exist_ok=True)

    tasks = load_dataset(args.dataset_dir)
    if args.ids:
        keep = {i.strip() for i in args.ids.split(",")}
        tasks = [t for t in tasks if t["id"] in keep]

    complete = make_completer(args.model)

    def log(line: str) -> None:
        print(line, flush=True)
        with (out_dir / "run.log").open("a") as f:
            f.write(line + "\n")

    log(f"model {complete.model_name}  tasks {len(tasks)}")
    sem = asyncio.Semaphore(args.concurrency)

    async def one(task):
        t0 = time.time()
        status = await predict_task(complete, task, out_dir, sem)
        elapsed_s = round(time.time() - t0, 1)
        log(f"{task['id']:<8} {elapsed_s:>6}s  {status}")
        line = {
            "id": task["id"],
            "output": f"outputs/{task['id']}.xlsx",
            "status": status,
            "elapsed_s": elapsed_s,
        }
        with (out_dir / "predictions.jsonl").open("a") as f:
            f.write(json.dumps(line) + "\n")

    run_t0 = time.time()
    await asyncio.gather(*(one(t) for t in tasks))
    log(f"total {round(time.time() - run_t0, 1)}s for {len(tasks)} tasks")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--ids", help="comma-separated task ids (default: all)")
    p.add_argument("--model", default="gemini:gemini-3.7-flash")
    p.add_argument("--concurrency", type=int, default=4)
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
