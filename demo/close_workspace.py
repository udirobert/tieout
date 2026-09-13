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
    import memory_store
    import memory_workbook

    return Path, json, memory_store, memory_workbook, mo


@app.cell
def _(mo):
    mo.md(
        "# Close memory — synthetic/local pilot\n\n"
        "Local-only governed correction memory. **No authentication, reviewer "
        "identity is self-attested text, and nothing here posts to any ledger or "
        "writes back to a source workbook.** Rules are immutable: a revoked rule "
        "can never be reactivated — a new correction produces a new rule at "
        "version 1 that must pass replay validation again."
    )


@app.cell
def _(mo):
    get_session, set_session = mo.state(None)
    get_result, set_result = mo.state({"message": "", "report": None})
    get_tick, set_tick = mo.state(0)
    return (
        get_result,
        get_session,
        get_tick,
        set_result,
        set_session,
        set_tick,
    )


@app.cell
def _(Path, get_tick, json, memory_store, memory_workbook, mo, set_result, set_session, set_tick):
    def _load(value):
        if value is None:
            return
        try:
            db = Path(value["db"]).expanduser()
            workbook = Path(value["workbook"]).expanduser() if value["workbook"].strip() else None
            records = memory_workbook.load_records(workbook) if workbook else []
            with memory_store.MemoryStore(db) as store:
                store.rules()
            set_session({"db": str(db), "workbook": str(workbook) if workbook else "", "records": records})
            set_result({"message": f"loaded {len(records)} record(s) from {db}", "report": None})
            set_tick(get_tick() + 1)
        except Exception as exc:
            set_session(None)
            set_result({"message": f"load failed: {exc}", "report": None})

    config_form = mo.ui.dictionary(
        {
            "db": mo.ui.text(value="/tmp/tieout-memory-demo/memory.sqlite3", label="memory db path (parent dir must exist)"),
            "workbook": mo.ui.text(label="transactions workbook (.xlsx)"),
        }
    ).form(submit_button_label="load / refresh", on_change=_load)
    mo.vstack([mo.md("## Workspace — load on explicit submit only"), config_form])


@app.cell
def _(get_result, json, mo):
    _result = get_result()
    _parts = [mo.plain_text(_result["message"] or "no action submitted yet")]
    if _result["report"] is not None:
        _parts.append(
            mo.accordion({"report": mo.plain_text(json.dumps(_result["report"], indent=2))})
        )
    mo.vstack(_parts)


@app.cell
def _(get_session, get_tick, memory_store, mo):
    _ = get_tick()
    _session = get_session()
    if _session is None:
        _view = mo.plain_text("no workspace loaded")
    else:
        _records = _session["records"]
        with memory_store.MemoryStore(_session["db"]) as _store:
            _suggestions = _store.suggest(_records) if _records else []
        _rows = [
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
        ]
        _view = mo.vstack(
            [
                mo.md("## Imported records — suggested vs review"),
                mo.ui.table(_rows, pagination=False) if _rows else mo.plain_text("no workbook records loaded"),
            ]
        )
    _view


@app.cell
def _(Path, get_session, get_tick, memory_store, mo, set_result, set_tick):
    _session = get_session()
    _records = _session["records"] if _session else []

    def _submit(value):
        if value is None:
            return
        _sess = get_session()
        if _sess is None:
            set_result({"message": "load a workspace first", "report": None})
            return
        try:
            _rec = next(r for r in _sess["records"] if r["record_id"] == value["record_id"])
            with memory_store.MemoryStore(Path(_sess["db"])) as _store:
                _correction = _store.record_correction(
                    _rec, value["vendor"], value["reviewer"], value["rationale"]
                )
                _rule = _store.propose(_correction["correction_id"])
            set_result({
                "message": (
                    f"correction {_correction['correction_id']} recorded; "
                    f"candidate rule {_rule['rule_id']} proposed — status candidate, not active"
                ),
                "report": _rule,
            })
            set_tick(get_tick() + 1)
        except Exception as exc:
            set_result({"message": f"correction failed: {exc}", "report": None})

    _options = {
        f"{r['source']['cell']} — {r['narrative']} [{r['scope']['entity']} / {r['scope']['account']}]": r["record_id"]
        for r in _records
    }
    correction_form = mo.ui.dictionary(
        {
            "record_id": mo.ui.dropdown(options=_options, label="record"),
            "vendor": mo.ui.text(label="vendor"),
            "reviewer": mo.ui.text(label="reviewer"),
            "rationale": mo.ui.text_area(label="rationale"),
        }
    ).form(submit_button_label="record correction + propose rule", on_change=_submit)
    mo.vstack([mo.md("## Record correction (proposes a candidate rule — never activates)"), correction_form])


@app.cell
def _(Path, get_session, get_tick, json, memory_store, mo, set_result, set_tick):
    _ = get_tick()
    _session = get_session()
    _entries = []
    if _session is not None:
        with memory_store.MemoryStore(Path(_session["db"])) as _store:
            _entries = _store.rules()

    def _apply(value):
        if value is None:
            return
        _sess = get_session()
        if _sess is None:
            set_result({"message": "load a workspace first", "report": None})
            return
        try:
            _action = value["action"]
            with memory_store.MemoryStore(Path(_sess["db"])) as _store:
                if _action == "validate":
                    _cases = json.loads(Path(value["cases"]).expanduser().read_text())
                    _report = _store.validate(value["rule_id"], _cases, value["reviewer"])
                    set_result({
                        "message": (
                            f"validation replay: eligible={_report['eligible']} cases={_report['cases']} "
                            f"improved={_report['improved']} regressions={_report['regressions']} "
                            f"incorrect={_report['incorrect']}"
                        ),
                        "report": _report,
                    })
                elif _action == "activate":
                    _event = _store.activate(value["rule_id"], value["reviewer"])
                    set_result({
                        "message": f"activated {value['rule_id']} by {_event['reviewer']} at {_event['created_at']}",
                        "report": _event["data"]["report"],
                    })
                elif _action == "revoke":
                    _event = _store.revoke(value["rule_id"], value["reviewer"], value["reason"])
                    set_result({"message": f"revoked {value['rule_id']} — reason: {_event['data']['reason']}", "report": _event})
                else:
                    set_result({"message": f"unknown action {_action!r}; no change made", "report": None})
                    return
            set_tick(get_tick() + 1)
        except Exception as exc:
            set_result({"message": f"action failed: {exc}", "report": None})

    _rule_options = {
        f"{e['rule']['rule_id']} [{e['status']}] {e['rule']['vendor']}": e["rule"]["rule_id"]
        for e in _entries
    }
    action_form = mo.ui.dictionary(
        {
            "rule_id": mo.ui.dropdown(options=_rule_options, label="rule"),
            "cases": mo.ui.text(label="replay_cases.json path (validate only)"),
            "reviewer": mo.ui.text(label="reviewer"),
            "action": mo.ui.radio(options=["validate", "activate", "revoke"], label="action"),
            "reason": mo.ui.text(label="revoke reason (revoke only)"),
        }
    ).form(submit_button_label="apply action", on_change=_apply)
    mo.vstack(
        [
            mo.md("## Governed actions — validate / activate / revoke"),
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
            else mo.plain_text("no rules yet"),
            action_form,
        ]
    )


@app.cell
def _(get_session, get_tick, json, memory_store, mo):
    _ = get_tick()
    _session = get_session()
    if _session is None:
        _view = mo.plain_text("")
    else:
        with memory_store.MemoryStore(_session["db"]) as _store:
            _entries = _store.rules()
            _history = _store.history()
        _provenance = {
            e["rule"]["rule_id"]: {"validation": e["validation"], "activation": e["activation"]}
            for e in _entries
        }
        _view = mo.vstack(
            [
                mo.md("## Provenance"),
                mo.accordion(
                    {
                        "rule validation + activation": mo.plain_text(json.dumps(_provenance, indent=2)),
                        "event history": mo.ui.table(
                            [
                                {k: v for k, v in h.items() if k != "data"}
                                for h in _history
                            ],
                            pagination=False,
                        ),
                    }
                ),
            ]
        )
    _view


@app.cell
def _(Path, get_session, get_tick, memory_store, memory_workbook, mo, set_result, set_tick):
    _session = get_session()

    def _export(value):
        if value is None:
            return
        _sess = get_session()
        if _sess is None:
            set_result({"message": "load a workspace first", "report": None})
            return
        if not _sess["workbook"]:
            set_result({"message": "no workbook loaded; nothing to export", "report": None})
            return
        try:
            with memory_store.MemoryStore(Path(_sess["db"])) as _store:
                _suggestions = memory_workbook.export_suggestions(
                    Path(_sess["workbook"]), Path(value["output"]).expanduser(), _store
                )
            set_result({"message": f"exported {len(_suggestions)} suggestion row(s) to {value['output']}", "report": None})
            set_tick(get_tick() + 1)
        except Exception as exc:
            set_result({"message": f"export failed: {exc}", "report": None})

    export_form = mo.ui.dictionary(
        {"output": mo.ui.text(label="review workbook output path (must not exist)")}
    ).form(submit_button_label="export review workbook", on_change=_export)
    mo.vstack(
        [
            mo.md(
                "## Export review workbook — writes a *new* file with a "
                "'tieout review' sheet; source workbook is never modified"
            ),
            export_form,
        ]
    )


if __name__ == "__main__":
    app.run()
