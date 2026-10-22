# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo>=0.24.2", "openpyxl"]
# ///
"""The close desk — the surface a finance team would actually use.

This is the product, not a demo of it. The console (`demo/console.py`) is the
instrument: it opens on a workspace picker that scans `/tmp`, which is how an
engineer gets at a run. This app opens on one thing — a close package — and
walks a reviewer through the five beats of an actual close:

    1 · load     paste a path, or pick the file
    2 · queue    the cells that need a person, each with its evidence and its diff
    3 · decide   approve or reject, through the one recorded write path
    4 · memory   teach the agent once; the rule is gated, not just stored
    5 · history  every decision this tenant has made, and what it cost

Three rules this surface does not break:

* **One write path.** Every decision goes through `exceptions.apply_decisions`.
  There is no second way to write a workbook from here.
* **Evidence is visible before the decision**, not after it. A reviewer sees
  the source rows and the current-to-proposed diff before choosing.
* **Every write is recorded.** Decisions are appended to the tenant's ledger
  before the workbooks are touched, so the record survives the artefact.

The tenant is explicit. A file belongs to one tenant, and this app opens that
tenant's ledger and memory — never another's.

Run:   uv run --directory research marimo run ../close_keeper/app.py
Check: research/.venv/bin/python close_keeper/app.py        (headless)
       research/.venv/bin/marimo check close_keeper/app.py  (static check)
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import sys
    from pathlib import Path

    import marimo as mo

    HERE = Path(__file__).resolve().parent
    ROOT = HERE.parent

    # The harness holds the machinery; this app only presents it.
    for sub in ("harness", "research"):
        path = str(ROOT / sub)
        if path not in sys.path:
            sys.path.insert(0, path)

    import close_metrics
    import exceptions as exc_mod
    import hmem_client
    import ledger as ledger_mod
    import memory_store as memory_store_mod

    return Path, close_metrics, exc_mod, hmem_client, ledger_mod, memory_store_mod, mo


@app.cell
def _(mo):
    mo.md("""
    # The close desk

    One package in. The cells that need a person, with their evidence.
    Every decision recorded.

    **A blank is an answer.** A cell the pipeline cannot verify is left
    blank and routed here with its source rows — never guessed. One
    recorded write path: `exceptions.apply_decisions`, the same function
    the CLI and the agent's tools call.

    > **Local pilot, not a hosted service.** Reviewer identity is
    > self-attested, and this runs on your machine. Nothing here posts to a
    > ledger or writes back to a source workbook.
    """)
    return


@app.cell
def _(mo):
    get_msg, set_msg = mo.state("nothing loaded")
    get_ws, set_ws = mo.state({})
    get_rev, set_rev = mo.state({})
    get_mem, set_mem = mo.state({})
    return get_mem, get_msg, get_rev, get_ws, set_msg, set_rev, set_ws


@app.cell
def _(Path, exc_mod, mo, set_msg, set_ws):
    """Load a close package: the workbook plus where its artifacts live."""

    def _load(value):
        if value is None:
            return
        _path = str(value.get("package") or "").strip()
        _tenant = str(value.get("tenant") or "").strip() or "local"
        if not _path:
            set_msg("paste the path to a close package (the run directory)")
            return
        _run_dir = Path(_path).expanduser()
        if not _run_dir.is_dir():
            set_msg(f"not a directory: {_run_dir}")
            return
        _exceptions_path = _run_dir / "exceptions.json"
        if not _exceptions_path.exists():
            set_msg(
                f"no exceptions.json in {_run_dir} — run the pipeline first "
                "(demo/simulate_demo.sh close-tieout-bank-cp)"
            )
            return
        try:
            _payloads, _as_array = exc_mod.load_exceptions(_exceptions_path)
        except Exception as exc:  # noqa: BLE001
            set_msg(f"could not read the queue: {exc}")
            return
        set_ws(
            {
                "run_dir": str(_run_dir),
                "exceptions_path": str(_exceptions_path),
                "payloads": _payloads,
                "as_array": _as_array,
                "tenant": _tenant,
                "ledger_path": str(_run_dir / f"ledger-{_tenant}.sqlite3"),
                "memory_path": str(_run_dir / f"memory-{_tenant}.sqlite3"),
            }
        )
        _total = sum(len(p.get("exceptions", [])) for p in _payloads)
        set_msg(f"loaded {_run_dir.name} — {_total} cell(s) need a decision")

    _loader = mo.ui.dictionary(
        {
            "package": mo.ui.text(
                label="close package (the run directory)",
                placeholder="/tmp/syndicate-demo",
            ),
            "tenant": mo.ui.text(label="tenant", value="local"),
        }
    ).form(submit_button_label="load", on_change=_load)

    load_block = mo.vstack(
        [
            mo.md(
                "## 1 · Load a close\n\nThe run directory holding `exceptions.json`."
            ),
            _loader,
        ]
    )
    return (load_block,)


@app.cell
def _(hmem_client, mo):
    """Integrations — which engines are actually attached, stated plainly.

    The desk never claims a capability it does not have, the same way the
    CLI reports recall live/off on stderr. Probes run once per render with
    short timeouts; a dead engine reads as off, never as an error banner.
    """
    import os

    _bits = []
    _want = os.environ.get("HMEM_SIDECAR_URL") or os.environ.get("CLOSE_KEEPER_HMEM")
    try:
        _hmem = bool(_want) and hmem_client.hmem_available(timeout=2)
    except Exception:  # noqa: BLE001
        _hmem = False
    _bits.append(
        f"**H-MEM recall:** {'live' if _hmem else 'off — governed store only'}"
    )
    if os.environ.get("ZETARIS_API_KEY"):
        try:
            import zetaris_client

            _z = zetaris_client.zetaris_available(timeout=3)
        except Exception:  # noqa: BLE001
            _z = False
        _bits.append(f"**Zetaris federation:** {'live' if _z else 'unreachable'}")
    else:
        _bits.append("**Zetaris federation:** off")
    _bits.append("**Seapoint:** per-session (agent surface)")
    integrations_block = mo.md(" · ".join(_bits))
    return (integrations_block,)


@app.cell
def _(get_msg, mo):
    message_block = mo.md(f"_{get_msg()}_")
    return (message_block,)


@app.cell
def _(exc_mod, get_rev, get_ws, mo):
    """The queue: every cell that needs a person, with its diff and its evidence."""
    _ = get_rev()
    _ws = get_ws()
    if not _ws:
        queue_block = mo.md("## 2 · The queue\n\n*load a close first*")
    else:
        _decisions = exc_mod.all_decisions(_ws["payloads"], _ws.get("tenant", ""))
        _rows = [
            {
                "cell": d.cell,
                "reason": d.reason,
                "now": d.current_value,
                "proposed": d.proposed_value,
                "evidence": d.evidence_label,
                "status": d.status,
            }
            for d in _decisions
        ]
        queue_block = mo.vstack(
            [
                mo.md(
                    f"## 2 · The queue — {len(_rows)} cell(s) need a decision\n\n"
                    "Each row is the unit of review: what the cell holds now, "
                    "what is proposed, and the source rows behind the proposal."
                ),
                (
                    mo.ui.table(_rows, pagination=False)
                    if _rows
                    else mo.md("*nothing to review — every answer cell verified*")
                ),
            ]
        )
    return (queue_block,)


@app.cell
def _(Path, exc_mod, get_rev, get_ws, ledger_mod, mo, set_msg, set_rev, time):
    """Decide: approve or reject, through the one recorded write path."""
    _ = get_rev()
    _ws = get_ws()
    if not _ws:
        decide_block = mo.md("")
    else:
        _decisions = exc_mod.all_decisions(_ws["payloads"], _ws.get("tenant", ""))
        _rows = [
            {
                "cell": d.cell,
                "reason": d.reason,
                "now": d.current_value,
                "proposed": d.proposed_value,
                "status": d.status,
            }
            for d in _decisions
        ]

        def _decide(value):
            if value is None:
                return
            _chosen = {r["cell"] for r in (value.get("rows") or [])}
            _verdict = value.get("decision")
            if not _chosen or not _verdict:
                set_msg("select at least one cell and a decision")
                return
            _status = "approved" if _verdict == "approve" else "rejected"
            for _payload in _ws["payloads"]:
                for _entry in _payload.get("exceptions", []):
                    if _entry["cell"] in _chosen:
                        _entry["status"] = _status
            _clean = {
                _payload["task_id"]: {
                    _entry["cell"]: _entry["status"]
                    for _entry in _payload.get("exceptions", [])
                    if _entry["cell"] in _chosen
                }
                for _payload in _ws["payloads"]
            }
            try:
                _ledger = ledger_mod.DecisionLedger(
                    Path(_ws["ledger_path"]), _ws.get("tenant") or None
                )
            except Exception as exc:  # noqa: BLE001
                set_msg(f"could not open the ledger: {exc}")
                return
            try:
                exc_mod.apply_decisions(
                    _ws["payloads"],
                    _clean,
                    _ws["exceptions_path"],
                    as_array=_ws["as_array"],
                    ledger=_ledger,
                    reviewer=str(value.get("reviewer") or "local-operator"),
                    tenant=_ws.get("tenant", ""),
                )
            except Exception as exc:  # noqa: BLE001
                set_msg(f"review failed: {exc}")
                return
            finally:
                _ledger.close()
            set_msg(
                f"{_status} {len(_chosen)} cell(s) — recorded in the ledger, "
                "then applied to the workbooks"
            )
            set_rev({"at": time.time()})

        _decision_form = mo.ui.dictionary(
            {
                "rows": mo.ui.table(
                    _rows, selection="multi", label="select the cells you decided"
                ),
                "decision": mo.ui.dropdown(
                    options=["approve", "reject"], label="decision"
                ),
                "reviewer": mo.ui.text(label="your name (self-attested)"),
            }
        ).form(submit_button_label="apply", on_change=_decide)

        decide_block = mo.vstack(
            [
                mo.md(
                    "## 3 · Decide\n\n"
                    "Approving writes the proposed value into the output "
                    "workbook; rejecting reverts the cell to the value it holds "
                    "now. Both go through `exceptions.apply_decisions`, and "
                    "both are recorded in the tenant's ledger *before* the "
                    "workbook is touched."
                ),
                _decision_form,
            ]
        )
    return (decide_block,)


@app.cell
def _(get_rev, get_ws, mo):
    """Where the full evidence lives, since a table column cannot hold it."""
    _ = get_rev()
    _ws = get_ws()
    if not _ws:
        evidence_block = mo.md("")
    else:
        evidence_block = mo.md(
            "**Evidence.** The table above abbreviates the source rows; the "
            "full list for every cell is in the tenant's ledger export, and "
            "`harness/close_metrics.py` reads the same records."
        )
    return (evidence_block,)


@app.cell
def _(Path, get_mem, get_rev, get_ws, hmem_client, memory_store_mod, mo, set_msg):
    """Teach the agent once: a correction becomes a candidate rule, gated."""
    _ = get_rev()
    _ = get_mem()
    _ws = get_ws()
    if not _ws:
        memory_block = mo.md("## 4 · Memory\n\n*load a close first*")
    else:
        try:
            _store = memory_store_mod.MemoryStore(
                Path(_ws["memory_path"]), _ws.get("tenant") or None
            )
            _rules = _store.rules()
            _store.close()
        except Exception as exc:  # noqa: BLE001
            _rules = []
            set_msg(f"could not open governed memory: {exc}")

        _rows = [
            {
                "id": r["rule"]["rule_id"][:8],
                "status": r["status"],
                "alias": r["rule"]["alias"],
                "vendor": r["rule"]["vendor"],
                "scope": r["rule"]["scope"]["entity"],
            }
            for r in _rules
        ]
        # The engine's own view: what the recall substrate holds for this
        # tenant, layered. Activation promotes to long_term; revocation marks
        # superseded — the record stays, penalized, never deleted.
        _engine_rows = []
        try:
            _client = hmem_client.HmemClient(_ws["tenant"])
            if _client.available():
                _engine_rows = [
                    {
                        "id": m["id"],
                        "layer": m["layer"],
                        "superseded": "yes" if m.get("supersededBy") else "",
                        "content": m["content"][:70],
                    }
                    for m in _client.all_memories()
                ]
        except Exception:  # noqa: BLE001 — engine off is not an error here
            _engine_rows = []
        _parts = [
            mo.md(
                "## 4 · Memory — what was learned, under governance\n\n"
                "A correction is evidence, not a rule. It becomes a rule "
                "only through record → propose → validate → activate, and "
                "the tools refuse an activation that has not cleared the "
                "replay gate."
            ),
            (
                mo.ui.table(_rows, pagination=False)
                if _rows
                else mo.md("*no rules yet*")
            ),
        ]
        if _engine_rows:
            _parts += [
                mo.md(
                    "**The engine's view.** H-MEM holds the recallable content "
                    "for this tenant — layered, scored, superseded rather than "
                    "deleted. This is what `suggest` recalls as evidence."
                ),
                mo.ui.table(_engine_rows, pagination=False),
            ]
        memory_block = mo.vstack(_parts)
    return (memory_block,)


@app.cell
def _(Path, get_rev, get_ws, hmem_client, ledger_mod, mo):
    """History: every decision this tenant has made — and the engine's own trail."""
    _ = get_rev()
    _ws = get_ws()
    if not _ws:
        history_block = mo.md("## 5 · History\n\n*load a close first*")
    else:
        try:
            _ledger = ledger_mod.DecisionLedger(
                Path(_ws["ledger_path"]), _ws.get("tenant") or None
            )
            _entries = _ledger.decisions()
            _ledger.close()
        except Exception:  # noqa: BLE001 — no ledger yet is not an error
            _entries = []
        _rows = [
            {
                "when": e.get("created_at", "")[:19].replace("T", " "),
                "cell": e.get("cell", ""),
                "decision": e.get("decision", ""),
                "reviewer": e.get("reviewer", ""),
                "evidence": "; ".join(
                    f"{r.get('sheet', '')} r{r.get('row', '')}"
                    for r in (e.get("evidence") or [])
                ),
            }
            for e in _entries
        ]
        # The second ledger: the engine logs its own actions (create, promote,
        # read, update) independently. Two trails that must agree — that is
        # the point of the design, so it is shown, not asserted.
        _engine_rows = []
        try:
            _client = hmem_client.HmemClient(_ws["tenant"])
            if _client.available():
                _engine_rows = [
                    {
                        "memory": e["memoryId"],
                        "action": e["action"],
                        "actor": e["actor"],
                    }
                    for e in _client.ledger()[-15:]
                ]
        except Exception:  # noqa: BLE001 — engine off is not an error here
            _engine_rows = []
        _parts = [
            mo.md(
                f"## 5 · History — {len(_rows)} recorded decision(s)\n\n"
                "Append-only. Deleting the workbooks does not erase this."
            ),
            (
                mo.ui.table(_rows, pagination=False)
                if _rows
                else mo.md("*no decisions recorded yet*")
            ),
        ]
        if _engine_rows:
            _parts += [
                mo.md(
                    "**The second ledger.** The memory engine logs its own "
                    "actions — create, promote, read, supersede — independently "
                    "of the decision ledger. Two trails that must agree."
                ),
                mo.ui.table(_engine_rows, pagination=False),
            ]
        history_block = mo.vstack(_parts)
    return (history_block,)


@app.cell
def _(Path, close_metrics, get_rev, get_ws, ledger_mod, memory_store_mod, mo):
    """What this close cost: the metrics, computed from what was recorded."""
    _ = get_rev()
    _ws = get_ws()
    if not _ws:
        metrics_block = mo.md("")
    else:
        _ledger = None
        _store = None
        try:
            _ledger = ledger_mod.DecisionLedger(
                Path(_ws["ledger_path"]), _ws.get("tenant") or None
            )
            try:
                _store = memory_store_mod.MemoryStore(
                    Path(_ws["memory_path"]), _ws.get("tenant") or None
                )
            except Exception:  # noqa: BLE001 — metrics work without the store
                _store = None
            _metrics = close_metrics.measure_close(
                _ws["payloads"],
                ledger=_ledger,
                store=_store,
                tenant=_ws.get("tenant", ""),
                dataset=Path(_ws["run_dir"]).name,
            )
        finally:
            if _ledger is not None:
                _ledger.close()
            if _store is not None:
                _store.close()
        metrics_block = mo.vstack(
            [
                mo.md("### What this close cost"),
                mo.md("```\n" + _metrics.render() + "\n```"),
            ]
        )
    return (metrics_block,)


if __name__ == "__main__":
    app.run()
