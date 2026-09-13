# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo>=0.24.2", "openpyxl"]
# ///
"""close-keeper live demo — the two things an agent for the close cannot fake.

Run:   uv run --directory research marimo run ../close_keeper/demo_app.py
Check: research/.venv/bin/python close_keeper/demo_app.py        (headless)
       research/.venv/bin/marimo check close_keeper/demo_app.py  (static check)

A guided walk through close-keeper's working agreement, in an ephemeral sandbox:

  1. The quiet run   — the close package was tied out; these cells need you
  2. Your decision   — approve / reject through the ONE recorded write path
  3. Teach it once   — a correction becomes a rule only through governance

The tie-out itself is seeded synthetic (`simulated` in the run status): the
Strands agent loop and the pipeline's model need API keys, and this sandbox
bundles none. Everything AFTER the run is fully real — `exceptions.apply_decisions`
and `memory_store` are the same functions the CLI and the agent's tools call,
with the same refusals. Run standalone on molab: the first cell clones the repo,
the second seeds the scratch workspace; each viewer gets their own sandbox.
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

    def _fetch_repo():
        """Clone the repo this notebook belongs to, once, into a cache dir.

        molab mirrors only this file; the demo also needs harness/, research/
        and demo/ beside it. Overrides: TIEOUT_REPO_URL (git URL or local path),
        TIEOUT_REPO_REF, TIEOUT_REPO_CACHE — for rehearsal against a checkout.
        """
        import os
        import subprocess

        cache = Path(
            os.environ.get(
                "TIEOUT_REPO_CACHE", str(Path.home() / ".cache" / "tieout-repo")
            )
        )
        if (cache / "harness").is_dir():
            return cache
        url = os.environ.get("TIEOUT_REPO_URL", "https://github.com/udirobert/tieout.git")
        ref = os.environ.get("TIEOUT_REPO_REF", "main")
        cache.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--branch", ref, url, str(cache)],
                check=True, capture_output=True, timeout=300,
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
    for _sub in ("harness", "research", "demo"):
        _path = str(REPO / _sub)
        if _path not in sys.path:
            sys.path.insert(0, _path)

    import exceptions as exc_mod
    import memory_scenario
    import memory_store
    import memory_workbook
    import sb
    from parsing import cell_ref

    return REPO, Path, cell_ref, exc_mod, json, memory_scenario, memory_store, memory_workbook, mo, sb, sys, time


@app.cell
def _(REPO, Path, cell_ref, exc_mod, memory_scenario, memory_store, sb):
    """Seed the scratch workspace when absent. Synthetic, and stamped as such.

    The run is a simulated partial tie-out: half the answer cells carry golden
    values, the rest are blank — blank routes to the exception queue, exactly as
    the real pipeline behaves. Status carries `simulated` so every surface flags
    it as construction, not model evidence. The memory workspace gets the
    scenario fixtures (transactions + labeled replay cases) and an EMPTY store:
    the viewer drives the governance lifecycle live.
    """
    import os
    import shutil

    import openpyxl

    _root = Path(os.environ.get("TIEOUT_SEED_DIR", "/tmp")) / "close-keeper-demo"
    run_dir = _root / "run"
    memory_dir = _root / "memory"
    seeded_note = ""

    if not (run_dir / "exceptions.json").exists():
        (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
        _dataset = Path(os.environ.get(
            "CLOSE_KEEPER_DATASET", str(REPO / "demo" / "close-tieout")
        ))
        for _task in sb.load_dataset(_dataset):
            _out = run_dir / "outputs" / f"{_task['id']}.xlsx"
            shutil.copy(_task["golden_xlsx"], _out)
            _wb = openpyxl.load_workbook(_out)
            _written = {}
            for _i, (_sheet, _coord) in enumerate(sb.answer_cells(_task, _wb)):
                _ws = _wb[_sheet] if _sheet in _wb.sheetnames else _wb.active
                if _i % 2 == 0:  # every other cell verified; the rest route to review
                    _written[cell_ref(_sheet or _ws.title, _coord)] = _ws[_coord].value
                else:
                    _ws[_coord] = None
            _wb.save(_out)
            _wb.close()
            exc_mod.write_exceptions(
                run_dir, _task,
                "ok: simulated partial tie-out",
                "close-keeper demo seed",
                {"written": _written},
                _out,
            )
        seeded_note = "run"

    if not (memory_dir / "memory.sqlite3").exists():
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_scenario.create_fixtures(memory_dir)
        with memory_store.MemoryStore(memory_dir / "memory.sqlite3"):
            pass  # schema only — the viewer drives the lifecycle
        seeded_note = (seeded_note + " + memory").strip(" +")

    seed_note = (
        "**Seeded synthetic sandbox** — a simulated partial tie-out (the Strands "
        "agent loop and the pipeline model need API keys; this sandbox bundles "
        "none) and an empty governed-memory store with labeled replay cases. "
        "Everything after the run is real: the write path and the governance "
        "gate are the same functions the CLI and the agent's tools call."
        if seeded_note
        else ""
    )
    return memory_dir, run_dir, seed_note


@app.cell
def _(mo, seed_note):
    mo.md(
        "# close-keeper — the close runs in the background; you're pinged only for real decisions\n\n"
        "An agent for finance professionals, built with the **Strands Agents SDK** on tieout's "
        "verified machinery. Its working agreement: **blank is an answer** (unverified cells route "
        "to you, with evidence — nothing is guessed), **one recorded write path** (a decision is "
        "persisted before any workbook cell changes), and **memory learns only through governance** "
        "(record → propose → validate → activate, enforced by the tools, not the prompt).\n\n"
        + (f"\n> ⚠ {seed_note}\n" if seed_note else "")
        + "\n**1 · the quiet run** — what needs you · **2 · your decision** — the one write path · "
        "**3 · teach it once** — governance-gated memory"
    )


@app.cell
def _(mo):
    get_msg, set_msg = mo.state("")
    get_rev, set_rev = mo.state({})
    get_mem, set_mem = mo.state({})
    get_memrev, set_memrev = mo.state({})
    return get_mem, get_memrev, get_msg, get_rev, set_mem, set_memrev, set_msg, set_rev


@app.cell
def _(get_rev, json, run_dir):
    """Reload the exception queue whenever a decision bumps the revision state."""
    _ = get_rev()
    review_payloads, review_as_array = [], True
    _path = run_dir / "exceptions.json"
    if _path.exists():
        _data = json.loads(_path.read_text(encoding="utf-8"))
        review_payloads, review_as_array = (
            (_data, True) if isinstance(_data, list) else ([_data], False)
        )
    review_rows = [
        {
            "task": p["task_id"],
            "cell": e["cell"],
            "reason": e["reason"],
            "proposed": e["proposed_value"],
            "status": e["status"],
        }
        for p in review_payloads
        for e in p.get("exceptions", [])
    ]
    return review_as_array, review_payloads, review_rows


@app.cell
def _(exc_mod, get_msg, mo, review_as_array, review_payloads, review_rows, run_dir, set_msg, set_rev, time):
    def _decide(value):
        if value is None:
            return
        _chosen = {(r["task"], r["cell"]) for r in (value.get("rows") or [])}
        _decision = value.get("decision")
        if not _chosen or not _decision:
            set_msg("select at least one row and a decision")
            return
        _status = "approved" if _decision == "approve" else "rejected"
        for _p in review_payloads:
            for _e in _p["exceptions"]:
                if (_p["task_id"], _e["cell"]) in _chosen:
                    _e["status"] = _status
        _decisions = {
            _p["task_id"]: {_e["cell"]: _e["status"] for _e in _p["exceptions"]}
            for _p in review_payloads
        }
        try:
            exc_mod.apply_decisions(
                review_payloads, _decisions, run_dir / "exceptions.json",
                as_array=review_as_array,
            )
        except Exception as _exc:  # noqa: BLE001
            set_msg(f"review failed: {_exc}")
            return
        set_msg(
            f"applied **{_status}** to {len(_chosen)} cell(s) — the decisions were "
            "persisted before any workbook was touched; rejected cells reverted to init"
        )
        set_rev({"at": time.time()})

    if review_rows:
        _form = mo.ui.dictionary(
            {
                "rows": mo.ui.table(review_rows, selection="multi", label="select rows, then decide"),
                "decision": mo.ui.dropdown(options=["approve", "reject"], label="decision"),
            }
        ).form(submit_button_label="apply decision", on_change=_decide)
    else:
        _form = mo.md("*no exceptions — every answer cell verified*")
    review_block = mo.vstack(
        [
            mo.md(
                "## 1 · The quiet run — these cells need you\n\n"
                f"The close package was tied out; **{len(review_rows)} cell(s)** could not be "
                "verified and routed here with evidence instead of a guess. Approving writes the "
                "proposed value; rejecting reverts to the init value — both through "
                "`exceptions.apply_decisions`, the one write path the agent has."
            ),
            _form,
            mo.md(get_msg()) if get_msg() else mo.md(""),
        ]
    )
    return (review_block,)


@app.cell
def _(get_memrev, json, memory_dir, memory_store, memory_workbook, mo):
    """Memory status — re-rendered whenever a governance step bumps the revision."""
    _ = get_memrev()
    with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
        _rules = _store.rules()
        _suggestions = _store.suggest(
            memory_workbook.load_records(memory_dir / "cycle2.xlsx")
        )
    _rule_rows = [
        {
            "rule": r["rule"]["rule_id"][:8],
            "status": r["status"],
            "alias": r["rule"]["alias"][:48],
            "vendor": r["rule"]["vendor"],
        }
        for r in _rules
    ]
    _sug_rows = [
        {
            "narrative": s["record"]["narrative"][:40],
            "entity": s["record"]["scope"]["entity"],
            "hint": s["record"]["vendor_hint"][:24],
            "decision": s["decision"],
            "vendor": s["vendor"] or "—",
        }
        for s in _suggestions
    ]
    memory_status = mo.vstack(
        [
            mo.md("### Memory right now"),
            mo.md("*no rules yet — teach one below*")
            if not _rule_rows
            else mo.ui.table(_rule_rows, pagination=False),
            mo.md(
                "**Next close's transactions** — what memory would do with them today. "
                "`review` means: route to a human, do not guess."
            ),
            mo.ui.table(_sug_rows, pagination=False),
        ]
    )
    return (memory_status,)


@app.cell
def _(get_mem, json, memory_dir, memory_store, memory_workbook, mo, set_mem, set_memrev, set_msg, time):
    def _stage():
        return dict(get_mem() or {})

    def _bump(note):
        set_msg(note)
        set_memrev({"at": time.time()})

    def _record(value):
        if value is None:
            return
        _reviewer = (value.get("reviewer") or "").strip()
        if not _reviewer:
            set_msg("a correction needs a self-attested reviewer name")
            return
        with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
            _rec = memory_workbook.load_records(memory_dir / "cycle1.xlsx")[0]
            _corr = _store.record_correction(
                _rec, "Example Services Ltd", _reviewer,
                "Demo: the vendor master identifies this exact narrative.",
            )
        _s = _stage()
        _s.update({"correction_id": _corr["correction_id"], "reviewer": _reviewer})
        _s.pop("rule_id", None)
        _s.pop("eligible", None)
        set_mem(_s)
        _bump(f"correction recorded (`{_corr['correction_id'][:8]}`) — evidence, not a rule. It changes nothing until proposed, validated and activated.")

    def _propose(value):
        if value is None:
            return
        _s = _stage()
        if not _s.get("correction_id"):
            set_msg("record a correction first (step 1)")
            return
        with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
            _rule = _store.propose(_s["correction_id"])
        _s["rule_id"] = _rule["rule_id"]
        set_mem(_s)
        _bump(f"candidate rule proposed (`{_rule['rule_id'][:8]}`) — still inert. Validate it against the labeled replay cases.")

    def _validate(value):
        if value is None:
            return
        _s = _stage()
        if not _s.get("rule_id"):
            set_msg("propose a candidate first (step 2)")
            return
        _cases = json.loads((memory_dir / "replay_cases.json").read_text())
        try:
            with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
                _report = _store.validate(_s["rule_id"], _cases, _s.get("reviewer", "viewer"))
        except Exception as _exc:  # noqa: BLE001
            set_msg(f"validation refused: {_exc}")
            return
        _s["eligible"] = bool(_report["eligible"])
        set_mem(_s)
        _cov = _report["coverage"]
        _bump(
            f"replay gate: **{'ELIGIBLE' if _report['eligible'] else 'NOT eligible'}** — "
            + ", ".join(f"{k}: {'✓' if v else '✗'}" for k, v in _cov.items())
            + f" · improved {_report['improved']}, regressions {_report['regressions']}"
        )

    def _activate(value):
        if value is None:
            return
        _s = _stage()
        if not _s.get("rule_id"):
            set_msg("no candidate to activate (steps 1–3 first)")
            return
        try:
            with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
                _store.activate(_s["rule_id"], _s.get("reviewer", "viewer"))
        except Exception as _exc:  # noqa: BLE001 — the refusal IS the demo
            set_msg(f"**activation refused** — {_exc}. The gate is enforced by the tool, not the prompt.")
            return
        _bump("rule **active** — watch the next-close table above flip from `review` to `suggested`. Nothing about the prompt changed; the store did.")

    def _revoke(value):
        if value is None:
            return
        _reason = (value.get("reason") or "").strip()
        _s = _stage()
        if not _s.get("rule_id"):
            set_msg("no rule to revoke")
            return
        if not _reason:
            set_msg("a revocation needs a recorded reason")
            return
        try:
            with memory_store.MemoryStore(memory_dir / "memory.sqlite3") as _store:
                _store.revoke(_s["rule_id"], _s.get("reviewer", "viewer"), _reason)
        except Exception as _exc:  # noqa: BLE001
            set_msg(f"**revoke refused** — {_exc}")
            return
        _bump("rule revoked — suggestions revert to `review`. The full event trail stays in the store.")

    _s = get_mem() or {}
    teach_block = mo.vstack(
        [
            mo.md(
                "## 3 · Teach it once — memory learns with permission\n\n"
                "A correction only becomes behavior through governance. Try activating before "
                "validating: the tool refuses. That refusal is the product."
            ),
            mo.hstack(
                [
                    mo.ui.dictionary(
                        {"reviewer": mo.ui.text(label="your name (self-attested)", value=_s.get("reviewer", ""))}
                    ).form(submit_button_label="1 · record correction", on_change=_record),
                    mo.ui.dictionary(
                        {"correction": mo.ui.text(label="correction", value=_s.get("correction_id", "")[:8], disabled=True)}
                    ).form(submit_button_label="2 · propose candidate", on_change=_propose),
                ]
            ),
            mo.hstack(
                [
                    mo.ui.dictionary(
                        {"rule": mo.ui.text(label="candidate", value=_s.get("rule_id", "")[:8], disabled=True)}
                    ).form(submit_button_label="3 · validate (replay gate)", on_change=_validate),
                    mo.ui.dictionary(
                        {"eligible": mo.ui.text(label="gate", value={True: "eligible", False: "not eligible"}.get(_s.get("eligible"), "—"), disabled=True)}
                    ).form(submit_button_label="4 · activate", on_change=_activate),
                    mo.ui.dictionary(
                        {"reason": mo.ui.text(label="reason", value="")}
                    ).form(submit_button_label="revoke", on_change=_revoke),
                ]
            ),
        ]
    )
    return (teach_block,)


@app.cell
def _(memory_status, mo, review_block, teach_block):
    mo.vstack(
        [
            review_block,
            mo.md("---\n## 2 · What memory learned"),
            memory_status,
            teach_block,
        ]
    )


@app.cell
def _(mo):
    mo.md(
        "\n".join(
            [
                "---",
                "## The architecture in one picture",
                "",
                "The agent loop is the thin part. Everything enforcement-shaped lives in "
                "the tools: `apply_review_decisions` is the only way to write a workbook, "
                "and `memory_store` is the only way a rule becomes active.",
            ]
        )
    )


@app.cell
def _(mo):
    mo.mermaid(
        """
        flowchart LR
            H["finance professional"] <-->|"only real decisions"| A["close-keeper<br/>Strands agent loop"]
            A --> T1["tie_out_workbook"]
            A --> T2["list_exceptions"]
            A --> T3["apply_review_decisions<br/>THE write path"]
            A --> T4["memory governance<br/>record → propose<br/>→ validate → activate"]
            T3 --> W[("workbook")]
            T4 --> M[("governed memory<br/>SQLite")]
        """
    )


@app.cell
def _(mo):
    mo.md(
        "\n".join(
            [
                "---",
                "**Repo + agent:** [github.com/udirobert/tieout](https://github.com/udirobert/tieout) "
                "— `close_keeper/` has the Strands agent (11 tools), the README, and the "
                "architecture. Run the full agent loop locally with your own keys:",
                "",
                "```bash",
                "uv sync --directory research --extra agent",
                "research/.venv/bin/python -m close_keeper \\",
                '  "Tie out the close package, then tell me which cells need my decision and why."',
                "```",
                "",
                "*Built for the Agents for Humans hackathon · Professional Agents track · MIT*",
            ]
        )
    )


if __name__ == "__main__":
    app.run()
