# Project workflow

- Run Python commands with `research/.venv/bin/python`, or `uv run --directory research` after syncing existing dependencies.
- Governed-memory unit tests: `research/.venv/bin/python -m unittest discover -s research -p 'test_memory_*.py' -v`.
- Static workspace check: `research/.venv/bin/marimo check demo/console.py` (console.py is the one UI surface; close_workspace.py and loop_dashboard.py are legacy utilities).
- The `close_keeper/` surface is the active one for the Agents for Humans hackathon (Strands Agents SDK, Professional track). See `close_keeper/README.md`. `demo/console.py` is the live tie-out console; `close_keeper/demo_app.py` is the key-free marimo walkthrough.
- Synthetic two-cycle scenario: `research/.venv/bin/python demo/memory_scenario.py --out-dir <new-directory>`. Preserve existing artifacts; the scenario refuses to overwrite them.
- Business memory is local SQLite and separate from the inference loop and live Neo4j graph. Do not run graph schema changes or upload workbook content implicitly.
- User requested stopping Playwright due to CPU impact. Do not restart browser automation or the marimo preview server without explicit permission. Reuse captured evidence and lightweight non-browser checks.
- Console browser verification (2026-09-13, ego-browser): all three tabs render, the memory write paths (correction → propose → validate, incl. the revoked-rule refusal) and live Aura retrieval verified against /tmp/syndicate-demo + a disposable fixture. The review-decision submit was deliberately not exercised against the demo dataset. The older apps remain unverified — see docs/COREWEAVE.md for the historical boundary.
- close-keeper end-to-end verification (2026-09-13, ego-browser): molab live demo app-view renders the seeded 29-row exception queue + decision review + governed memory lifecycle; the activation refusal fires when validate is skipped. Cedar policies in `close_keeper/policies/` are authored against the AgentCore Policy docs (not yet exercised against a live Gateway).
- Do not run concurrent experimental loops: they share harness/skills_overlay.json. Do not describe the repeatedly inspected CFO demo dataset as an untouched lockbox.
