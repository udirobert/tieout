"""Zero-credential GPU eval: serve an open model with vLLM, predict, score.

    uv run gpu_eval.py --out-dir /tmp/gpu-eval --sample 5
    uv run gpu_eval.py --out-dir /tmp/gpu-eval --model Qwen/Qwen3-32B --all

Built for molab's free GPU containers (RTX Pro 6000): no API keys, no hosted
inference — the model is pulled from Hugging Face, served locally over the
OpenAI-compatible API, and scored by the same grader every baseline uses
(evaluate.py). Everything lands in --out-dir: predictions.jsonl, outputs/,
traces/, run.log, results.json.

Deliberately plain: the prediction path reuses baseline/common.py's prompt,
parse and output contract, so a score here is comparable to the OpenRouter
baselines. LibreOffice recalculation runs when soffice is present
(--install-libreoffice tries apt); otherwise scoring falls back to --no-recalc
and the summary says so.

Blackwell note (verified on molab's RTX Pro 6000, 2026-09): vllm 0.29 + torch
2.13 (cu13) serve sm_120 fine. Two molab-specific traps: the container has no
CUDA toolkit, so flashinfer's JIT sampler crashes warmup with "Could not find
nvcc" — start_server sets VLLM_USE_FLASHINFER_SAMPLER=0 to take the torch
sampler path instead (if it still crashes, `pip uninstall flashinfer-python`
in the venv is the known-good config). vLLM 0.29 also renamed
--disable-log-requests, so this script passes no logging flags.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "baseline"))
sys.path.insert(0, str(HERE))

from sb import DEFAULT_DATASET, load_dataset, soffice_path  # noqa: E402

DEFAULT_MODEL = "Qwen/Qwen3-8B"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out-dir", required=True)
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--dataset-dir", default=str(DEFAULT_DATASET))
    p.add_argument("--ids", help="comma-separated task ids")
    p.add_argument("--sample", type=int, help="first N tasks in dataset order")
    p.add_argument("--all", action="store_true", help="score every task in the dataset")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=8192,
                   help="per-task generation cap; matches baseline/tinker_predict.py (default 8192)")
    p.add_argument("--no-thinking", action="store_true",
                   help="Qwen3-style models: pass enable_thinking=false via chat_template_kwargs "
                        "for direct JSON answers (faster, more parseable; different model behavior)")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--server-url",
                   help="use an already-running OpenAI-compatible server (http://host:port/v1) "
                        "instead of starting vLLM — also skips the GPU check and vLLM install")
    p.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    p.add_argument("--max-model-len", type=int, default=None)
    p.add_argument("--install-libreoffice", action="store_true",
                   help="apt-get libreoffice-calc so the scorer can recalculate formulas")
    p.add_argument("--server-timeout", type=int, default=1800,
                   help="seconds to wait for model download + vLLM health (default 1800)")
    p.add_argument("--keep-server", action="store_true", help="leave vLLM running at the end")
    return p.parse_args()


def log(msg: str) -> None:
    print(f"[gpu-eval {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ensure_dataset(dataset_dir: Path) -> None:
    if (dataset_dir / "dataset.json").exists():
        return
    log(f"dataset missing at {dataset_dir} — running data/download.py")
    subprocess.run([sys.executable, str(HERE / "data" / "download.py")], check=True)


def ensure_package(module: str, pip_spec: str) -> None:
    if importlib.util.find_spec(module) is not None:
        return
    log(f"installing {pip_spec} (module {module} not importable)")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", pip_spec], check=True
    )


def check_gpu() -> str:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        raise SystemExit(
            "no GPU visible (nvidia-smi failed). On molab, attach one first: "
            "notebook specs button in the app header."
        )
    log(f"GPU: {out}")
    return out


def maybe_install_libreoffice(enabled: bool) -> None:
    if soffice_path():
        return
    if not enabled:
        return
    log("installing libreoffice-calc via apt (so the scorer can recalculate)")
    subprocess.run(["apt-get", "update", "-qq"], check=False)
    subprocess.run(
        ["apt-get", "install", "-y", "-qq", "libreoffice-calc"], check=False
    )
    log(f"soffice after install: {soffice_path() or 'still missing — scoring with --no-recalc'}")


def start_server(args: argparse.Namespace) -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", args.model,
        "--port", str(args.port),
        "--gpu-memory-utilization", str(args.gpu_memory_utilization),
    ]
    if args.max_model_len:
        cmd += ["--max-model-len", str(args.max_model_len)]
    log("starting vLLM: " + " ".join(cmd))
    # molab's runtime image has no nvcc; keep vLLM off flashinfer's JIT sampler path
    env = dict(os.environ, VLLM_USE_FLASHINFER_SAMPLER="0")
    proc = subprocess.Popen(cmd, env=env)
    url = f"http://127.0.0.1:{args.port}/health"
    deadline = time.time() + args.server_timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(
                f"vLLM exited during startup (code {proc.returncode}). On Blackwell "
                "(sm_120) GPUs a stable vLLM wheel may not match the container's "
                "CUDA — install a wheel built for it and retry."
            )
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    log(f"vLLM healthy after {int(args.server_timeout - (deadline - time.time()))}s")
                    return proc
        except OSError:
            pass
        time.sleep(5)
    proc.kill()
    raise SystemExit(f"vLLM not healthy after {args.server_timeout}s")


async def predict(args: argparse.Namespace, tasks: list[dict]) -> None:
    from openai import AsyncOpenAI

    from common import run as run_predictions

    base_url = args.server_url or f"http://127.0.0.1:{args.port}/v1"
    client = AsyncOpenAI(base_url=base_url, api_key="EMPTY")
    # same prompt contract as the Tinker baseline: system prompt + FORMAT_HINT, temp 0, 8192 cap
    from common import FORMAT_HINT, SYSTEM_PROMPT

    extra = {}
    if args.no_thinking:
        extra["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}

    async def complete(prompt: str):
        resp = await client.chat.completions.create(
            model=args.model,
            temperature=0,
            max_tokens=args.max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt + FORMAT_HINT},
            ],
            **extra,
        )
        usage = resp.usage
        return (
            resp.choices[0].message.content or "",
            usage.prompt_tokens if usage else None,
            usage.completion_tokens if usage else None,
        )

    await run_predictions(
        complete, f"vllm:{args.model}", tasks, Path(args.out_dir), args.concurrency
    )


def score(args: argparse.Namespace, tasks: list[dict]) -> dict:
    out_dir = Path(args.out_dir)
    cmd = [
        sys.executable, str(HERE / "evaluate.py"),
        "--predictions", str(out_dir / "predictions.jsonl"),
        "--dataset-dir", args.dataset_dir,
        "--out", str(out_dir / "results.json"),
    ]
    if args.all:
        cmd.append("--all")
    elif args.ids:
        cmd += ["--ids", args.ids]
    if not soffice_path():
        log("no soffice — scoring with --no-recalc (formula tasks score raw values)")
        cmd.append("--no-recalc")
    log("scoring: " + " ".join(cmd))
    subprocess.run(cmd, check=True)
    results = json.loads((out_dir / "results.json").read_text())
    return results


def main() -> None:
    args = parse_args()
    if not args.server_url:
        check_gpu()
    ensure_dataset(Path(args.dataset_dir))
    maybe_install_libreoffice(args.install_libreoffice)
    ensure_package("openai", "openai")
    if not args.server_url:
        ensure_package("vllm", "vllm")

    tasks = load_dataset(args.dataset_dir)
    if args.ids:
        wanted = {i.strip() for i in args.ids.split(",") if i.strip()}
        tasks = [t for t in tasks if t["id"] in wanted]
    elif args.sample:
        tasks = tasks[: args.sample]
    log(f"{len(tasks)} task(s) queued against {args.model}")

    server = None
    if args.server_url:
        log(f"using external server: {args.server_url}")
    else:
        server = start_server(args)
    try:
        asyncio.run(predict(args, tasks))
        results = score(args, tasks)
    finally:
        if server is not None and not args.keep_server:
            log("stopping vLLM")
            server.terminate()
            try:
                server.wait(timeout=60)
            except subprocess.TimeoutExpired:
                server.kill()

    summary = results.get("summary", results)
    log(f"done — summary: {json.dumps(summary)[:400]}")
    log(f"artifacts in {args.out_dir} (predictions.jsonl, outputs/, traces/, results.json)")


if __name__ == "__main__":
    main()
