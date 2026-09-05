"""Official-shaped values-first clone-run (task_0019 measurement).

Does not change the ship pipeline. One-shot, thinking via cookbook qwen3_5
renderer + parse_response. Full 120×30 serialize, official FORMAT_HINT, no
skills / pin / repair. Our parse_answer + write_output. max_tokens 16384.

  python harness/clone_run.py --dataset-dir /data --out-dir /tmp/clone-run-400
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "baseline"))

from common import FORMAT_HINT, SYSTEM_PROMPT, build_prompt  # noqa: E402
from sb import load_dataset  # noqa: E402

from parsing import parse_answer  # noqa: E402
from pipeline import _ensure_output, write_output  # noqa: E402

DEFAULT_MODEL = "Qwen/Qwen3.8-27B"
RENDERER_NAME = "qwen3_5"
MAX_TOKENS = 16384


def _load_env() -> None:
    for env_path in (ROOT / ".env", ROOT / "research" / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _already_predicted(pred_path: Path) -> set[str]:
    done: set[str] = set()
    if not pred_path.exists():
        return done
    for line in pred_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            done.add(json.loads(line)["id"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def _make_completer(base_model: str, model_path: str | None, max_tokens: int):
    import tinker
    from tinker import types
    from tinker_cookbook import renderers
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    client = tinker.ServiceClient(
        project_id=os.environ.get("TINKER_PROJECT_ID") or None
    )
    sampler = client.create_sampling_client(
        base_model=base_model, model_path=model_path or None
    )
    tokenizer = get_tokenizer(base_model)
    renderer = renderers.get_renderer(RENDERER_NAME, tokenizer)
    stops = renderer.get_stop_sequences()
    params = types.SamplingParams(
        max_tokens=max_tokens, temperature=0.0, stop=stops
    )

    async def complete(prompt: str) -> tuple[str, int, int]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt + FORMAT_HINT},
        ]
        model_input = renderer.build_generation_prompt(messages)
        response = await sampler.sample_async(
            prompt=model_input, num_samples=1, sampling_params=params
        )
        tokens = response.sequences[0].tokens
        content = renderer.parse_response(tokens)[0]["content"]
        if not isinstance(content, str):
            content = "".join(
                part.get("text", "")
                for part in content
                if part.get("type") == "text"
            )
        return content, model_input.length, len(tokens)

    complete.model_name = model_path or f"{base_model}+{RENDERER_NAME}"
    return complete


def _is_json_decode_error(exc: BaseException) -> bool:
    if isinstance(exc, json.JSONDecodeError):
        return True
    name = type(exc).__name__
    msg = str(exc).lower()
    return name == "JSONDecodeError" or "no json" in msg or "json" in name.lower()


async def predict_one(complete, task: dict, out_dir: Path, max_tokens: int) -> dict:
    out = out_dir / "outputs" / f"{task['id']}.xlsx"
    prompt = build_prompt(task)
    started = time.time()
    audit = {
        "id": task["id"],
        "json_decode_error": False,
        "truncated": False,
        "input_tokens": None,
        "output_tokens": None,
        "status": None,
        "error": None,
    }
    text = ""
    try:
        text, in_tok, out_tok = await complete(prompt)
        audit["input_tokens"] = in_tok
        audit["output_tokens"] = out_tok
        audit["truncated"] = bool(out_tok is not None and out_tok >= max_tokens)
        try:
            answer = parse_answer(text)
        except Exception as e:
            audit["json_decode_error"] = _is_json_decode_error(e)
            raise
        write_output(task, answer, out)
        audit["status"] = "ok"
    except Exception as e:  # noqa: BLE001 — never-blank
        audit["error"] = f"{type(e).__name__}: {e}"[:300]
        if audit["status"] is None:
            audit["status"] = f"error: {audit['error']}"[:200]
        if not audit["json_decode_error"]:
            audit["json_decode_error"] = _is_json_decode_error(e)
    _ensure_output(task, out)
    latency_ms = int((time.time() - started) * 1000)
    trace = {
        "step": 1,
        "model": getattr(complete, "model_name", "clone"),
        "prompt": prompt,
        "response": text or None,
        "input_tokens": audit["input_tokens"],
        "output_tokens": audit["output_tokens"],
        "latency_ms": latency_ms,
        "error": audit["error"],
        "json_decode_error": audit["json_decode_error"],
        "truncated": audit["truncated"],
    }
    with (out_dir / "traces" / f"{task['id']}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False, default=str) + "\n")
    with (out_dir / "parse_audit.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(audit, ensure_ascii=False) + "\n")
    return audit


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-dir", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--ids", help="comma-separated task ids (default: all, dataset order)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--model-path", default=None)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    p.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument("--fresh", action="store_true")
    args = p.parse_args()
    _load_env()

    out_dir = Path(args.out_dir)
    if args.fresh:
        for name in ("predictions.jsonl", "run.log", "parse_audit.jsonl"):
            pth = out_dir / name
            if pth.exists():
                pth.write_text("", encoding="utf-8")
        for sub in ("outputs", "traces"):
            shutil.rmtree(out_dir / sub, ignore_errors=True)
    for sub in ("outputs", "traces"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    (out_dir / "run.log").touch(exist_ok=True)
    (out_dir / "parse_audit.jsonl").touch(exist_ok=True)

    tasks = load_dataset(args.dataset_dir)
    if args.ids:
        keep = {i.strip() for i in args.ids.split(",") if i.strip()}
        tasks = [t for t in tasks if t["id"] in keep]
    skipped = 0
    if args.resume:
        done = _already_predicted(out_dir / "predictions.jsonl")
        if done:
            before = len(tasks)
            tasks = [t for t in tasks if t["id"] not in done]
            skipped = before - len(tasks)

    complete = _make_completer(args.model, args.model_path, args.max_tokens)

    def log(line: str) -> None:
        print(line, flush=True)
        with (out_dir / "run.log").open("a") as f:
            f.write(line + "\n")

    log(
        f"clone-run  model {getattr(complete, 'model_name', args.model)}  "
        f"renderer {RENDERER_NAME} thinking=on  temp 0  max_tokens {args.max_tokens}  "
        f"tasks {len(tasks)}" + (f"  resume-skip {skipped}" if skipped else "")
    )
    sem = asyncio.Semaphore(args.concurrency)

    async def one(task):
        async with sem:
            t0 = time.time()
            audit = await predict_one(complete, task, out_dir, args.max_tokens)
        elapsed_s = round(time.time() - t0, 1)
        flags = (
            f"json_err={int(audit['json_decode_error'])}  "
            f"trunc={int(audit['truncated'])}  "
            f"out_tok={audit['output_tokens']}"
        )
        log(f"{task['id']:<8} {elapsed_s:>6}s  {audit['status']}  {flags}")
        line = {
            "id": task["id"],
            "output": f"outputs/{task['id']}.xlsx",
            "status": audit["status"],
            "elapsed_s": elapsed_s,
            "json_decode_error": audit["json_decode_error"],
            "truncated": audit["truncated"],
            "output_tokens": audit["output_tokens"],
        }
        with (out_dir / "predictions.jsonl").open("a") as f:
            f.write(json.dumps(line) + "\n")

    run_t0 = time.time()
    await asyncio.gather(*(one(t) for t in tasks))
    log(f"total {round(time.time() - run_t0, 1)}s for {len(tasks)} tasks")

    audits = []
    for line in (out_dir / "parse_audit.jsonl").read_text().splitlines():
        if line.strip():
            audits.append(json.loads(line))
    summary = {
        "n": len(audits),
        "json_decode_error": sum(1 for a in audits if a.get("json_decode_error")),
        "truncated": sum(1 for a in audits if a.get("truncated")),
        "both": sum(
            1
            for a in audits
            if a.get("json_decode_error") and a.get("truncated")
        ),
        "ok": sum(1 for a in audits if a.get("status") == "ok"),
    }
    (out_dir / "parse_audit_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    log(
        f"audit  n={summary['n']}  json_decode_error={summary['json_decode_error']}  "
        f"truncated={summary['truncated']}  both={summary['both']}  ok={summary['ok']}"
    )
    _flush_out_dir(out_dir)


def _fsync_file(path: Path) -> None:
    if not path.exists():
        return
    fd = os.open(path, os.O_APPEND)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _flush_out_dir(out_dir: Path) -> None:
    """fsync ship artifacts so a force-exit cannot drop the last writes."""
    sys.stdout.flush()
    sys.stderr.flush()
    pred = out_dir / "predictions.jsonl"
    if not pred.exists():
        pred.write_text("", encoding="utf-8")
    for name in ("predictions.jsonl", "run.log"):
        _fsync_file(out_dir / name)
    out_fd = os.open(out_dir, os.O_RDONLY)
    try:
        os.fsync(out_fd)
    finally:
        os.close(out_fd)
    if not pred.exists() or not (out_dir / "run.log").exists() or not (out_dir / "outputs").is_dir():
        raise SystemExit("ship outputs missing after flush")


if __name__ == "__main__":
    # Tinker SessionFuturesPoller stays pending after main(); judges need a real exit.
    import traceback

    code = 0
    try:
        asyncio.run(main())
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
