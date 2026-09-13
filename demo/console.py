"""tieout console — one marimo app over the three surfaces.

Run:   uv run --directory research marimo run ../demo/console.py
Check: research/.venv/bin/python demo/console.py        (headless: runs every cell)
       research/.venv/bin/marimo check demo/console.py  (static dataflow check)

Three tabs over artifacts a run already produced:

  Run     what happened — per-cell grading against golden, the exception queue
          (approve/reject), and the self-improvement curve when there is one
  Memory  the governed correction memory — records, candidate rules,
          validate / activate / revoke, provenance, review-workbook export
  Graph   where each answer came from — lineage reconstructed offline from
          artifacts, plus live counterparty retrieval on explicit submit

Read-only by default. The only writes are review decisions and governed rule
actions, both behind an explicit form submit and both through the same functions
the CLIs use (`exceptions.apply_decisions`, `memory_store`). Nothing here posts to
a ledger or writes back to a source workbook.

The Graph tab needs no database: `rebuild_graph.lineage_from_artifacts()` replays
each task through the same `graph_payload()` the live run used, reading output
workbooks with `save=False` so finished artifacts are never rewritten. Rendering
the tab never connects — `graph.configured()` inspects the environment only,
because `graph.enabled()` would ensure schema on page load.

Every write is a form `on_change` callback rather than a `mo.ui.button` read in
the cell body. A callback fires only on submit; a button value is a dependency, so
a cell that both reads it and bumps the state it depends on can re-run itself.
"""

import marimo

__generated_with = "0.24.2"
app = marimo.App()


@app.cell
def _():
    import json
    import sys
    import time
    from pathlib import Path

    import marimo as mo

    HERE = Path(__file__).resolve().parent
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import ui_common

    ui_common.bootstrap()

    import exceptions as exc_mod
    import graph
    import memory_store
    import memory_workbook
    import rebuild_graph
    import sb

    return (
        Path,
        exc_mod,
        graph,
        json,
        memory_store,
        memory_workbook,
        mo,
        rebuild_graph,
        sb,
        time,
        ui_common,
    )


@app.cell
def _(mo, ui_common):
    mo.md(
        "# tieout console\n\n"
        + ui_common.BOUNDARY
        + "\n\n**Run** — what happened · **Memory** — what was learned, under "
        "governance · **Graph** — where each answer came from.\n\n"
        "Load a workspace below. Nothing is read until you submit, and nothing is "
        "written until you submit an action."
    )


@app.cell
def _(mo):
    get_msg, set_msg = mo.state("no workspace loaded")
    get_rev, set_rev = mo.state({})
    get_mem, set_mem = mo.state({})
    get_ws, set_ws = mo.state({})
    return get_mem, get_msg, get_rev, get_ws, set_mem, set_msg, set_rev, set_ws


@app.cell
def _(Path, mo, set_msg, set_ws, ui_common):
    def _load(value):
        if value is None:
            return
        run = str(value.get("run") or "")
        db = str(value.get("db") or "")
        workbook = str(value.get("workbook") or "")
        if run and not Path(run).is_dir():
            set_msg(f"not a directory: {run}")
            return
        if db and not Path(db).is_file():
            set_msg(f"not a file: {db}")
            return
        if workbook and not Path(workbook).is_file():
            set_msg(f"not a file: {workbook}")
            return
        if not (run or db):
            set_msg("pick a run dir, a memory db, or both")
            return
        set_ws({"run": run, "db": db, "workbook": workbook})
        parts = []
        if run:
            parts.append(f"run {run}")
        if db:
            parts.append(f"memory {db}")
        if workbook:
            parts.append(f"records {Path(workbook).name}")
        set_msg("loaded " + " · ".join(parts))

    picker = mo.ui.dictionary(
        {
            "run": mo.ui.dropdown(
                options=ui_common.run_choices(), label="run dir", value=None
            ),
            "db": mo.ui.dropdown(
                options=ui_common.memory_choices(),
                label="governed memory db",
                value=None,
            ),
            "workbook": mo.ui.dropdown(
                options=ui_common.workbook_choices(),
                label="transactions workbook (Memory tab records)",
                value=None,
            ),
        }
    ).form(submit_button_label="load workspace", on_change=_load)
    mo.vstack(
        [
            mo.md(
                "## Workspace — load on explicit submit only\n\n"
                "Scanned once at start from `/tmp` and `runs/` (two levels). Restart "
                "the app to re-scan."
            ),
            picker,
        ]
    )


@app.cell
def _(get_msg, mo):
    _msg = get_msg()
    # Italic for one-liners only: a multi-line message (e.g. the retrieval
    # result) would leak the literal underscores.
    mo.md(f"_{_msg}_" if "\n" not in _msg else _msg)


# ---------------------------------------------------------------------------
# Shared load: one read of the artifacts feeds the Run and Graph tabs, so the two
# can never disagree about what a cell holds.
# ---------------------------------------------------------------------------
@app.cell
def _(Path, exc_mod, get_rev, get_ws, json, rebuild_graph, sb):
    _ = get_rev()
    _ws = get_ws()
    payloads, as_array, lineages, skipped, loop, tasks = [], True, [], [], [], {}
    run_dir = Path(_ws["run"]) if _ws and _ws.get("run") else None
    exc_path = None
    if run_dir is not None:
        candidate = run_dir / "exceptions.json"
        if candidate.exists():
            exc_path = candidate
            try:
                payloads, as_array = exc_mod.load_exceptions(candidate)
            except (OSError, ValueError) as _exc:
                payloads, as_array = [], True
        try:
            tasks = {t["id"]: t for t in sb.load_dataset(rebuild_graph.DEFAULT_DATASET)}
        except (OSError, StopIteration, ValueError):
            tasks = {}
        try:
            lineages, skipped, _unstamped = rebuild_graph.lineage_from_artifacts(
                run_dir, rebuild_graph.DEFAULT_DATASET
            )
        except Exception:  # noqa: BLE001 — a missing dataset must not blank the tab
            lineages, skipped = [], [("dataset", "unreadable")]
        log = run_dir / "loop_log.jsonl"
        if log.exists():
            loop = [
                json.loads(ln)
                for ln in log.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
    return as_array, exc_path, lineages, loop, payloads, run_dir, skipped, tasks


@app.cell
def _(loop, mo, run_dir):
    if run_dir is None:
        curve_block = mo.md("*load a run dir*")
    elif not loop:
        curve_block = mo.md(
            "### Self-improvement curve\n\n*no `loop_log.jsonl` in this run dir — "
            "this was a single pass, not a loop*"
        )
    else:
        scores = [r["cell_accuracy"] for r in loop if "cell_accuracy" in r]

        def _sparkline(vals, w=460, h=90):
            if len(vals) < 2:
                return "<i>need 2+ iterations for a curve</i>"
            lo, hi = min(vals), max(vals)
            span = (hi - lo) or 1e-9
            pts = " ".join(
                f"{10 + i * (w - 20) / (len(vals) - 1):.1f},"
                f"{h - 12 - (v - lo) / span * (h - 24):.1f}"
                for i, v in enumerate(vals)
            )
            return (
                f'<svg width="{w}" height="{h}" style="border:1px solid #ccc">'
                f'<polyline points="{pts}" fill="none" stroke="#f5b800" '
                f'stroke-width="2.5"/>'
                f'<text x="10" y="{h - 4}" font-size="11">{lo:.3f}</text>'
                f'<text x="{w - 45}" y="14" font-size="11">{hi:.3f}</text></svg>'
            )

        curve_block = mo.vstack(
            [
                mo.md("### Self-improvement curve — cell_accuracy per iteration"),
                mo.Html(_sparkline(scores)),
                mo.ui.table(loop, pagination=True),
            ]
        )
    return curve_block


@app.cell
def _(lineages, mo, sb, tasks, ui_common):
    """Per-cell grading, derived from the same lineage the Graph tab renders."""
    if not lineages:
        grading_block = mo.md("### Grading\n\n*load a run dir to grade it*")
    else:
        _rows, _banners, _correct, _total = [], [], 0, 0
        for _lin in lineages:
            _task = tasks.get(_lin["task_id"])
            _golden = (_task or {}).get("golden_xlsx")
            _gold = sb.load_answer_values(_golden, _task) if _golden and _task else {}
            if not _gold:
                _banners.append(f"`{_lin['task_id']}`: no golden workbook, not graded")
            if ui_common.simulated(_lin):
                _banners.append(
                    f"`{_lin['task_id']}`: status `{_lin['status']}` — written by "
                    "`demo/simulate_demo.sh`, so its score is construction, not "
                    "model evidence"
                )
            for _cell in _lin["cells"]:
                _want = _gold.get((_cell["sheet"], _cell["coord"]))
                _ok = sb.values_equal(_want, _cell["value"]) if _gold else None
                if _gold:
                    _total += 1
                    _correct += bool(_ok)
                _rows.append(
                    {
                        "task": _lin["task_id"],
                        "cell": _cell["coord"],
                        "header": _cell["header"],
                        "written": _cell["value"],
                        "golden": _want if _gold else "",
                        "correct": "" if _ok is None else ("yes" if _ok else "NO"),
                        "matched": _cell["vendor_key"] or "",
                        "exception": (_cell["exception"] or {}).get("reason", ""),
                    }
                )
        _head = [mo.md("### Grading — every answer cell against golden")]
        _head.extend(mo.md(f"> ⚠ {b}") for b in _banners)
        if _total:
            _head.append(
                mo.md(
                    f"**{_correct}/{_total} answer cells match golden** — same "
                    "`sb.values_equal` the benchmark scorer uses, applied to the "
                    "lineage values rather than a re-read of the workbook"
                )
            )
        _head.append(mo.ui.table(_rows, pagination=True))
        grading_block = mo.vstack(_head)
    return grading_block


@app.cell
def _(
    as_array,
    exc_mod,
    exc_path,
    mo,
    payloads,
    run_dir,
    set_msg,
    set_rev,
    time,
):
    if run_dir is None:
        review_block = mo.md("### Exception review\n\n*load a run dir*")
    elif exc_path is None:
        per_task = (run_dir / "exceptions").is_dir()
        review_block = mo.md(
            "### Exception review\n\n*no aggregate `exceptions.json` here*"
            + (
                " — this run wrote only per-task `exceptions/*.json`, which the "
                "review CLI handles; the console reviews the aggregate file."
                if per_task
                else "."
            )
        )
    else:
        _payloads, _exc_path, _as_array = payloads, exc_path, as_array

        def _decide(value):
            if value is None:
                return
            chosen = {(r["task"], r["cell"]) for r in (value.get("rows") or [])}
            decision = value.get("decision")
            if not chosen or not decision:
                set_msg("select at least one row and a decision")
                return
            status = "approved" if decision == "approve" else "rejected"
            for payload in _payloads:
                for entry in payload["exceptions"]:
                    if (payload["task_id"], entry["cell"]) in chosen:
                        entry["status"] = status
            decisions = {
                payload["task_id"]: {
                    entry["cell"]: entry["status"] for entry in payload["exceptions"]
                }
                for payload in _payloads
            }
            try:
                exc_mod.apply_decisions(
                    _payloads, decisions, _exc_path, as_array=_as_array
                )
            except Exception as exc:  # noqa: BLE001
                set_msg(f"review failed: {exc}")
                return
            set_msg(
                f"applied {status} to {len(chosen)} exception(s); decisions "
                "persisted before the workbooks were touched"
            )
            set_rev({"at": time.time()})

        _rows = [
            {
                "task": payload["task_id"],
                "cell": entry["cell"],
                "reason": entry["reason"],
                "proposed": entry["proposed_value"],
                "status": entry["status"],
            }
            for payload in payloads
            for entry in payload["exceptions"]
        ]
        if _rows:
            _form = mo.ui.dictionary(
                {
                    "rows": mo.ui.table(
                        _rows, selection="multi", label="select rows, then decide"
                    ),
                    "decision": mo.ui.dropdown(
                        options=["approve", "reject"], label="decision"
                    ),
                }
            ).form(submit_button_label="apply decision", on_change=_decide)
        else:
            _form = mo.md("*no exceptions raised — every answer cell verified*")
        review_block = mo.vstack(
            [
                mo.md(
                    f"### Exception review — {len(_rows)} row(s)\n\n"
                    "Approving writes the proposed value into the output workbook; "
                    "rejecting reverts the cell to its init value. Both go through "
                    "`exceptions.apply_decisions`, the one write path the CLI uses."
                ),
                _form,
            ]
        )
    return review_block


@app.cell
def _(curve_block, grading_block, mo, review_block, run_dir):
    run_tab = (
        mo.md("## Run — what happened\n\n*load a run dir*")
        if run_dir is None
        else mo.vstack([grading_block, review_block, curve_block])
    )
    return run_tab


# ---------------------------------------------------------------------------
# Memory tab: display and forms are separate cells on purpose. In marimo a cell
# is not re-run by a state change it initiated itself — so a cell that both
# renders db contents and owns the callbacks that mutate the db (as this used
# to be) shows stale tables after every write. Here `memory_display` reads
# `get_mem` and owns no callbacks; the two form cells call `set_mem` and render
# no db state of their own (the actions form reads `get_mem` only so its rule
# dropdown picks up newly proposed rules — after its own submit its labels go
# stale, but the display cell above always re-renders the truth).
# ---------------------------------------------------------------------------
@app.cell
def _(Path, get_mem, get_ws, json, memory_store, memory_workbook, mo):
    _ = get_mem()
    _ws = get_ws()
    _db = Path(_ws["db"]) if _ws and _ws.get("db") else None
    _workbook = Path(_ws.get("workbook")) if _ws and _ws.get("workbook") else None

    if _db is None or not _db.is_file():
        memory_display_block = mo.md(
            "## Memory — governed corrections\n\n"
            "*pick a governed memory db in the workspace picker — "
            "`demo/memory_scenario.py --out-dir <new-dir>` produces one*"
        )
    else:
        _warn = ""
        try:
            _records = memory_workbook.load_records(_workbook) if _workbook else []
        except Exception as exc:  # noqa: BLE001
            _records = []
            _warn = f"records failed to load from `{_workbook}`: {exc}"

        try:
            with memory_store.MemoryStore(_db) as _store:
                _entries = _store.rules()
                _history = _store.history()
                _suggestions = _store.suggest(_records) if _records else []
        except Exception as exc:  # noqa: BLE001
            memory_display_block = mo.md(
                f"## Memory — governed corrections\n\n*cannot open `{_db}`: {exc}*"
            )
        else:
            _blocks = [
                mo.md(
                    "## Memory — governed corrections\n\nRules are immutable: a revoked "
                    "rule can never be reactivated. A new correction produces a new rule "
                    "at version 1 that must pass replay validation again. This SQLite "
                    "memory is the authority for approved business rules; the Neo4j "
                    "graph is not."
                ),
                mo.md(
                    f"**db:** `{_db}` · **rules:** {len(_entries)} · **events:** "
                    f"{len(_history)} · **records:** {len(_records)}"
                    + (f" from `{_workbook.name}`" if _workbook else " — none loaded")
                ),
            ]
            if _warn:
                _blocks.append(mo.md(f"> ⚠ {_warn}"))

            if _suggestions:
                _blocks.append(mo.md("### Imported records — suggested vs review"))
                _blocks.append(
                    mo.ui.table(
                        [
                            {
                                "record_id": s["record"]["record_id"],
                                "tenant": s["record"]["scope"]["tenant"],
                                "entity": s["record"]["scope"]["entity"],
                                "account": s["record"]["scope"]["account"],
                                "currency": s["record"]["scope"]["currency"],
                                "cell": s["record"]["source"]["cell"],
                                "narrative": s["record"]["narrative"],
                                "vendor_hint": s["record"]["vendor_hint"],
                                "decision": s["decision"],
                                "proposed_vendor": s["vendor"],
                                "reason": s["reason"],
                                "rule_ids": " ".join(s["rule_ids"]),
                            }
                            for s in _suggestions
                        ],
                        pagination=False,
                    )
                )

            _blocks.append(mo.md("### Rules"))
            _blocks.append(
                mo.ui.table(
                    [
                        {
                            "id": e["rule"]["rule_id"],
                            "status": e["status"],
                            "scope": json.dumps(e["rule"]["scope"], sort_keys=True),
                            "alias": e["rule"]["alias"],
                            "vendor": e["rule"]["vendor"],
                        }
                        for e in _entries
                    ],
                    pagination=False,
                )
                if _entries
                else mo.md("*no rules yet*")
            )

            _blocks.append(mo.md("### Provenance"))
            _blocks.append(
                mo.accordion(
                    {
                        "rule validation + activation": mo.plain_text(
                            json.dumps(
                                {
                                    e["rule"]["rule_id"]: {
                                        "validation": e["validation"],
                                        "activation": e["activation"],
                                    }
                                    for e in _entries
                                },
                                indent=2,
                            )
                        ),
                        "event history": mo.ui.table(
                            [
                                {k: v for k, v in h.items() if k != "data"}
                                for h in _history
                            ],
                            pagination=False,
                        ),
                    }
                )
            )
            memory_display_block = mo.vstack(_blocks)
    return memory_display_block


@app.cell
def _(Path, get_ws, memory_store, memory_workbook, mo, set_mem, set_msg, time):
    _ws = get_ws()
    _db = Path(_ws["db"]) if _ws and _ws.get("db") else None
    _workbook = Path(_ws.get("workbook")) if _ws and _ws.get("workbook") else None

    if _db is None or not _db.is_file():
        correction_block = mo.md("")
    else:
        try:
            _records = memory_workbook.load_records(_workbook) if _workbook else []
        except Exception:  # noqa: BLE001 — the display cell already names the failure
            _records = []

        def _correct(value):
            if value is None:
                return
            record = next(
                (r for r in _records if r["record_id"] == value.get("record_id")), None
            )
            if record is None:
                set_msg("pick a record to correct — records come from the workbook")
                return
            try:
                with memory_store.MemoryStore(_db) as _store:
                    correction = _store.record_correction(
                        record, value["vendor"], value["reviewer"], value["rationale"]
                    )
                    rule = _store.propose(correction["correction_id"])
            except Exception as exc:  # noqa: BLE001
                set_msg(f"correction failed: {exc}")
                return
            set_msg(
                f"correction {correction['correction_id']} recorded; candidate rule "
                f"{rule['rule_id']} proposed — status candidate, not active"
            )
            set_mem({"at": time.time()})

        _record_options = {
            f"{r['source']['cell']} — {r['narrative']} [{r['scope']['entity']}]": r[
                "record_id"
            ]
            for r in _records
        } or {"no records loaded — pick a transactions workbook": ""}
        correction_block = mo.vstack(
            [
                mo.md(
                    "### Record correction (proposes a candidate rule — never activates)"
                ),
                mo.ui.dictionary(
                    {
                        "record_id": mo.ui.dropdown(
                            options=_record_options, label="record"
                        ),
                        "vendor": mo.ui.text(label="vendor"),
                        "reviewer": mo.ui.text(label="reviewer"),
                        "rationale": mo.ui.text_area(label="rationale"),
                    }
                ).form(
                    submit_button_label="record correction + propose rule",
                    on_change=_correct,
                ),
            ]
        )
    return correction_block


@app.cell
def _(
    Path,
    get_mem,
    get_ws,
    json,
    memory_store,
    memory_workbook,
    mo,
    set_mem,
    set_msg,
    time,
):
    _ = get_mem()
    _ws = get_ws()
    _db = Path(_ws["db"]) if _ws and _ws.get("db") else None
    _workbook = Path(_ws.get("workbook")) if _ws and _ws.get("workbook") else None

    if _db is None or not _db.is_file():
        actions_block = mo.md("")
    else:

        def _act(value):
            if value is None:
                return
            action = value.get("action")
            try:
                with memory_store.MemoryStore(_db) as _store:
                    if action == "validate":
                        cases = json.loads(
                            Path(value["cases"])
                            .expanduser()
                            .read_text(encoding="utf-8")
                        )
                        report = _store.validate(
                            value["rule_id"], cases, value["reviewer"]
                        )
                        set_msg(
                            f"validation replay: eligible={report['eligible']} "
                            f"cases={report['cases']} improved={report['improved']} "
                            f"regressions={report['regressions']} "
                            f"incorrect={report['incorrect']}"
                        )
                    elif action == "activate":
                        event = _store.activate(value["rule_id"], value["reviewer"])
                        set_msg(
                            f"activated {event['rule_id']} by {event['reviewer']} at "
                            f"{event['created_at']}"
                        )
                    elif action == "revoke":
                        event = _store.revoke(
                            value["rule_id"], value["reviewer"], value["reason"]
                        )
                        set_msg(
                            f"revoked {event['rule_id']} — reason: "
                            f"{event['data']['reason']}"
                        )
                    else:
                        set_msg(f"unknown action {action!r}; no change made")
                        return
            except Exception as exc:  # noqa: BLE001
                set_msg(f"action failed: {exc}")
                return
            set_mem({"at": time.time()})

        def _export(value):
            if value is None:
                return
            if _workbook is None:
                set_msg("no transactions workbook loaded; nothing to export against")
                return
            output = Path(value["output"]).expanduser()
            try:
                with memory_store.MemoryStore(_db) as _store:
                    written = memory_workbook.export_suggestions(
                        _workbook, output, _store
                    )
            except Exception as exc:  # noqa: BLE001
                set_msg(f"export failed: {exc}")
                return
            set_msg(
                f"exported {len(written)} suggestion row(s) to {output} — a new file; "
                "the source workbook was not modified"
            )

        try:
            with memory_store.MemoryStore(_db) as _store:
                _entries = _store.rules()
        except Exception:  # noqa: BLE001 — the display cell already names the failure
            _entries = []

        _rule_options = {
            f"{e['rule']['rule_id']} [{e['status']}] {e['rule']['vendor']}": e["rule"][
                "rule_id"
            ]
            for e in _entries
        } or {"no rules yet": ""}
        _cases_default = _db.parent / "replay_cases.json"
        _export_default = (
            f"{_workbook.parent / (_workbook.stem + '-reviewed.xlsx')}"
            if _workbook
            else ""
        )
        actions_block = mo.vstack(
            [
                mo.md("### Governed actions — validate / activate / revoke"),
                mo.ui.dictionary(
                    {
                        "rule_id": mo.ui.dropdown(options=_rule_options, label="rule"),
                        "cases": mo.ui.text(
                            value=str(_cases_default)
                            if _cases_default.exists()
                            else "",
                            label="replay_cases.json path (validate only)",
                        ),
                        "reviewer": mo.ui.text(label="reviewer"),
                        "action": mo.ui.radio(
                            options=["validate", "activate", "revoke"], label="action"
                        ),
                        "reason": mo.ui.text(label="revoke reason (revoke only)"),
                    }
                ).form(submit_button_label="apply action", on_change=_act),
                mo.md(
                    "### Export review workbook — writes a *new* file with a "
                    "`tieout review` sheet; the source workbook is never modified"
                ),
                mo.ui.dictionary(
                    {
                        "output": mo.ui.text(
                            value=_export_default,
                            label="review workbook output path (must not exist)",
                        )
                    }
                ).form(submit_button_label="export review workbook", on_change=_export),
            ]
        )
    return actions_block


@app.cell
def _(actions_block, correction_block, memory_display_block, mo):
    memory_tab = mo.vstack([memory_display_block, correction_block, actions_block])
    return memory_tab


@app.cell
def _(graph, lineages, mo, run_dir, skipped, ui_common):
    _blocks = [
        mo.md(
            "## Graph — where each answer came from\n\n"
            "Lineage is reconstructed **offline** from this run's artifacts — no "
            "database connection, and output workbooks are read with `save=False` so "
            "nothing is rewritten. The graph is a derived index: everything below is "
            "rebuildable from `exceptions.json` + `outputs/*.xlsx` + the dataset."
        )
    ]
    if run_dir is None:
        _blocks.append(mo.md("*load a run dir*"))
    else:
        if skipped:
            _blocks.extend(
                mo.md(f"> ⚠ skipped `{task}`: {why}") for task, why in skipped
            )
        if not lineages:
            _blocks.append(
                mo.md("*no lineage could be reconstructed from this run dir*")
            )
        for lin in lineages:
            if ui_common.simulated(lin):
                _blocks.append(
                    mo.md(
                        f"> ⚠ **`{lin['task_id']}` has status `{lin['status']}`** — "
                        "written by `demo/simulate_demo.sh`. Its score is "
                        "construction, not model evidence."
                    )
                )
            cells = lin["cells"]
            matched = sum(1 for c in cells if c["vendor_key"])
            raised = sum(1 for c in cells if c["exception"])
            _blocks.append(
                mo.md(
                    f"### `{lin['task_id']}` — run `{lin['run_id']}` · status "
                    f"`{lin['status']}`\n\n{len(cells)} answer cells · {matched} "
                    f"matched into the counterparty master · {raised} routed to the "
                    "exception queue"
                )
            )
            _blocks.append(
                mo.ui.table(
                    [
                        {
                            "cell": c["coord"],
                            "header": c["header"],
                            "value": c["value"],
                            "derived from": ", ".join(d["coord"] for d in c["derived"]),
                            "source values": " | ".join(
                                str(d["value"])[:40] for d in c["derived"]
                            ),
                            "vendor_key": c["vendor_key"] or "",
                            "match": c["match_method"] or "",
                            "evidence rows": len(c["evidence"]),
                            "exception": (c["exception"] or {}).get("reason", ""),
                        }
                        for c in cells
                    ],
                    pagination=False,
                )
            )
            blanks = [c["coord"] for c in cells if c["value"] in (None, "")]
            if blanks:
                _blocks.append(
                    mo.md(
                        "Left blank on purpose — no match the agent could justify: "
                        f"**{', '.join(blanks)}**. Blank is the correct answer for an "
                        "unmatched row; it routes to a human instead of guessing."
                    )
                )
    _blocks.append(mo.md(f"_graph backend: {graph.configured()}_"))
    graph_tab = mo.vstack(_blocks)
    return graph_tab


@app.cell
def _(graph, mo, set_msg):
    def _query(value):
        if value is None:
            return
        names = [
            n.strip() for n in str(value.get("names") or "").splitlines() if n.strip()
        ]
        if not names:
            set_msg("enter one pulled counterparty name per line")
            return
        try:
            block = graph.query_vendor_context(names, k=5)
        except Exception as exc:  # noqa: BLE001 — retrieval must never break the tab
            set_msg(f"retrieval failed: {exc}")
            return
        set_msg(
            block
            or "connected, but no candidates returned — the exactness gate would "
            "leave these blank"
        )

    retrieval_block = mo.vstack(
        [
            mo.md(
                "### Counterparty retrieval (live Aura, read-only)\n\n"
                "What the agent is handed for a bank narrative. `[exact]` is the only "
                "marker the prompt authorises it to write; anything else is a similar "
                "name it must leave blank. Submitting connects (`graph.init_graph()`, "
                "which ensures the schema's `IF NOT EXISTS` indexes) — rendering this "
                "tab does not. Needs `NEO4J_*` in `.env` and an awake instance; "
                "without them this returns nothing and says so. The candidate scan is "
                "not reimplemented here, so what you see is what the agent saw."
            ),
            mo.ui.dictionary(
                {
                    "names": mo.ui.text_area(
                        label="pulled name(s), one per line", value="NIP LIT"
                    )
                }
            ).form(submit_button_label="retrieve candidates", on_change=_query),
        ]
    )
    return retrieval_block


@app.cell
def _(graph_tab, memory_tab, mo, retrieval_block, run_tab):
    mo.ui.tabs(
        {
            "Run": run_tab,
            "Memory": memory_tab,
            "Graph": mo.vstack([graph_tab, retrieval_block]),
        },
        lazy=True,
    )


if __name__ == "__main__":
    app.run()
