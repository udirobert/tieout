# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo>=0.24.2"]
# ///
"""molab GPU eval runner — serve an open model on the free GPU, score it, download the artifacts.

Mirror on molab: https://molab.marimo.io/github/udirobert/tieout/blob/main/research/molab_gpu_eval.py

Attach the GPU first (notebook specs button in the app header), then set the
parameters and press run. The first run is slow: pip-installs vLLM, downloads
the model from Hugging Face (~16 GB for the default 8B), downloads the dataset
(15 MB), then serves + predicts + scores. Everything lands in the out dir;
the last cell offers predictions.jsonl and results.json as downloads.

Zero credentials by construction: open weights, public dataset, no API keys.
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import json
    import subprocess
    import sys
    import time
    from pathlib import Path

    import marimo as mo

    HERE = Path(__file__).resolve().parent

    def _fetch_repo():
        """Same bootstrap as demo/console.py: molab mirrors only this file."""
        import os

        cache = Path(
            os.environ.get(
                "TIEOUT_REPO_CACHE", str(Path.home() / ".cache" / "tieout-repo")
            )
        )
        if (cache / "harness").is_dir():
            return cache
        url = os.environ.get(
            "TIEOUT_REPO_URL", "https://github.com/udirobert/tieout.git"
        )
        ref = os.environ.get("TIEOUT_REPO_REF", "main")
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, url, str(cache)],
                check=True,
                capture_output=True,
                timeout=300,
            )
        except Exception:  # noqa: BLE001 — no git in the container: tarball fallback
            import tarfile
            import tempfile
            import urllib.request

            tarball = (
                url.removesuffix(".git").replace("github.com", "codeload.github.com")
                + f"/tar.gz/refs/heads/{ref}"
            )
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / "repo.tar.gz"
                urllib.request.urlretrieve(tarball, archive)
                with tarfile.open(archive) as tf:
                    tf.extractall(tmp, filter="data")
                extracted = next(p for p in Path(tmp).iterdir() if p.is_dir())
                extracted.rename(cache)
        return cache

    REPO = HERE.parent if (HERE.parent / "harness").is_dir() else _fetch_repo()
    return Path, REPO, json, mo, subprocess, sys, time


@app.cell
def _(mo, subprocess):
    import shutil

    _nv = shutil.which("nvidia-smi")
    _gpu = ""
    if _nv:
        _r = subprocess.run(
            [_nv, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
        )
        _gpu = _r.stdout.strip()
    mo.md(
        "# GPU eval — open model, zero API keys\n\n"
        + (
            f"**GPU:** `{_gpu}`"
            if _gpu
            else "**No GPU attached** — attach one via the notebook specs button "
            "in the app header before pressing run."
        )
        + "\n\nServes an open model with vLLM on this container, predicts against "
        "SpreadsheetBench Verified-400 tasks, and scores with the same grader as "
        "every baseline (`research/evaluate.py`). First run installs vLLM and "
        "downloads the model (~16 GB for the default 8B) — expect several minutes."
    )


@app.cell
def _(mo):
    get_args, set_args = mo.state(None)
    return get_args, set_args


@app.cell
def _(Path, mo, set_args):
    def _submit(value):
        if value is not None:
            set_args(value)

    mo.vstack(
        [
            mo.md("## Parameters"),
            mo.ui.dictionary(
                {
                    "model": mo.ui.text(
                        value="Qwen/Qwen3-8B", label="HF model id (public weights)"
                    ),
                    "sample": mo.ui.number(
                        value=5, start=1, stop=400, label="first N tasks (ignored if ids set)"
                    ),
                    "ids": mo.ui.text(
                        label="or exact task ids, comma-separated (overrides sample)"
                    ),
                    "concurrency": mo.ui.number(value=8, start=1, stop=64, label="concurrency"),
                    "out": mo.ui.text(value="/tmp/gpu-eval", label="out dir"),
                    "libreoffice": mo.ui.checkbox(
                        label="install libreoffice-calc (apt) for formula recalculation in scoring"
                    ),
                }
            ).form(submit_button_label="run eval", on_change=_submit),
        ]
    )


@app.cell
def _(Path, REPO, get_args, json, mo, subprocess, sys, time):
    _args = get_args()
    if _args is None:
        run_view = mo.md("*set parameters and press run eval*")
    else:
        _cmd = [
            sys.executable,
            str(REPO / "research" / "gpu_eval.py"),
            "--out-dir",
            str(_args["out"]),
            "--model",
            str(_args["model"]),
            "--concurrency",
            str(_args["concurrency"]),
        ]
        if str(_args.get("ids") or "").strip():
            _cmd += ["--ids", str(_args["ids"]).strip()]
        else:
            _cmd += ["--sample", str(_args["sample"])]
        if _args.get("libreoffice"):
            _cmd.append("--install-libreoffice")

        _started = time.time()
        _proc = subprocess.run(
            _cmd, capture_output=True, text=True, timeout=4 * 3600
        )
        _elapsed = int(time.time() - _started)
        _tail = "\n".join((_proc.stdout or "").splitlines()[-60:])
        _err_tail = "\n".join((_proc.stderr or "").splitlines()[-30:])

        _blocks = [
            mo.md(
                f"## Run finished — exit {_proc.returncode} in {_elapsed // 60}m{_elapsed % 60}s"
            )
        ]
        _results_path = Path(_args["out"]) / "results.json"
        if _results_path.exists():
            _results = json.loads(_results_path.read_text())
            _blocks.append(
                mo.plain_text(json.dumps(_results.get("summary", _results), indent=2))
            )
            _blocks.append(
                mo.hstack(
                    [
                        mo.download(
                            data=(Path(_args["out"]) / "predictions.jsonl").read_bytes(),
                            filename="predictions.jsonl",
                        ),
                        mo.download(
                            data=_results_path.read_bytes(), filename="results.json"
                        ),
                    ]
                )
            )
        if _tail:
            _blocks.append(mo.accordion({"run.log tail": mo.plain_text(_tail)}))
        if _proc.returncode != 0 and _err_tail:
            _blocks.append(mo.accordion({"stderr tail": mo.plain_text(_err_tail)}))
        run_view = mo.vstack(_blocks)
    return run_view


if __name__ == "__main__":
    app.run()
