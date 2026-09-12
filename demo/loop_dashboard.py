"""tieout loop dashboard — marimo app (CoreWeave Hacks).

Run: uv run --directory ../research marimo run loop_dashboard.py
(or: cd research && uv run marimo run ../demo/loop_dashboard.py)

Shows the self-improvement curve (loop_log.jsonl per-iteration scores) and a
human-review table for exceptions.json — approve/reject applies decisions to
the output workbooks, same as the CLI reviewer.
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import json
    import sys
    from pathlib import Path

    import marimo as mo

    ROOT = Path(__file__).resolve().parent.parent if "__file__" in dir() else Path.cwd().parent
    sys.path.insert(0, str(ROOT / "harness"))
    sys.path.insert(0, str(ROOT / "research"))
    return Path, json, mo, ROOT, sys


@app.cell
def _(mo):
    loop_dir = mo.ui.text(value="/tmp/tieout-loop", label="loop out-dir")
    exceptions_path = mo.ui.text(
        value="/tmp/tieout-loop/iter0/exceptions.json", label="exceptions.json"
    )
    refresh = mo.ui.button(label="reload", kind="neutral")
    mo.vstack([loop_dir, exceptions_path, refresh])
    return loop_dir, exceptions_path, refresh


@app.cell
def _(Path, json, loop_dir, mo, refresh):
    _ = refresh.value
    log_path = Path(loop_dir.value) / "loop_log.jsonl"
    iters = []
    if log_path.exists():
        iters = [
            json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()
        ]
    scores = [r["cell_accuracy"] for r in iters if "cell_accuracy" in r]
    return iters, scores, log_path


@app.cell
def _(iters, mo, scores):
    def _sparkline(vals, w=420, h=90):
        if len(vals) < 2:
            return "<i>need 2+ iterations for a curve</i>"
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or 1e-9
        pts = " ".join(
            f"{10 + i * (w - 20) / (len(vals) - 1):.1f},{h - 12 - (v - lo) / span * (h - 24):.1f}"
            for i, v in enumerate(vals)
        )
        return (
            f'<svg width="{w}" height="{h}" style="border:1px solid #ccc">'
            f'<polyline points="{pts}" fill="none" stroke="#f5b800" stroke-width="2.5"/>'
            f'<text x="10" y="{h - 4}" font-size="11">{lo:.3f}</text>'
            f'<text x="{w - 45}" y="14" font-size="11">{hi:.3f}</text></svg>'
        )

    mo.vstack(
        [
            mo.md("## Self-improvement loop — cell_accuracy per iteration"),
            mo.Html(_sparkline(scores)),
            mo.ui.table(iters, pagination=False) if iters else mo.md("*no loop_log.jsonl yet*"),
        ]
    )


@app.cell
def _(Path, exceptions_path, json, mo, refresh, sys):
    _ = refresh.value
    payloads = []
    p = Path(exceptions_path.value)
    if p.exists():
        data = json.loads(p.read_text())
        payloads = data if isinstance(data, list) else [data]
    rows = [
        {
            "task": pl["task_id"],
            "cell": e["cell"],
            "reason": e["reason"],
            "proposed": e["proposed_value"],
            "status": e["status"],
        }
        for pl in payloads
        for e in pl["exceptions"]
    ]
    table = mo.ui.table(rows, selection="multi", label="exceptions — select to review")
    mo.vstack([mo.md("## Exception queue"), table])
    return table, payloads, rows


@app.cell
def _(mo):
    approve = mo.ui.button(label="approve selected")
    reject = mo.ui.button(label="reject selected")
    mo.hstack([approve, reject])
    return approve, reject


@app.cell
def _(approve, exceptions_path, mo, payloads, reject, rows, table):
    decision = None
    if approve.value:
        decision = "approved"
    elif reject.value:
        decision = "rejected"
    if decision and table.value:
        chosen = {(r["task"], r["cell"]) for r in table.value}
        for pl in payloads:
            for e in pl["exceptions"]:
                if (pl["task_id"], e["cell"]) in chosen:
                    e["status"] = decision
        import json as _json
        from pathlib import Path as _P

        _p = _P(exceptions_path.value)
        _p.write_text(_json.dumps(payloads, indent=2, default=str) + "\n")
        try:
            import exceptions as exc_mod

            decisions = {}
            for pl in payloads:
                decisions[pl["task_id"]] = {
                    e["cell"]: e["status"] for e in pl["exceptions"]
                }
            exc_mod._apply_decisions(payloads, decisions)
            msg = f"applied {decision} to {len(chosen)} exception(s) and updated workbooks"
        except Exception as e:  # noqa: BLE001
            msg = f"statuses saved; workbook apply failed: {e}"
    else:
        msg = "select rows, then approve or reject"
    mo.md(f"**{msg}**")


if __name__ == "__main__":
    app.run()
