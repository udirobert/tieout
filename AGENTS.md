# Project workflow

- Run Python commands with `research/.venv/bin/python`, or `uv run --directory research` after syncing existing dependencies.
- Governed-memory unit tests: `research/.venv/bin/python -m unittest discover -s research -p 'test_memory_*.py' -v`.
- Static workspace check: `research/.venv/bin/marimo check demo/close_workspace.py`.
- Synthetic two-cycle scenario: `research/.venv/bin/python demo/memory_scenario.py --out-dir <new-directory>`. Preserve existing artifacts; the scenario refuses to overwrite them.
- Business memory is local SQLite and separate from the inference loop and live Neo4j graph. Do not run graph schema changes or upload workbook content implicitly.
- User requested stopping Playwright due to CPU impact. Do not restart browser automation or the marimo preview server without explicit permission. Reuse captured evidence and lightweight non-browser checks.
- Revised callback UI browser verification is incomplete. See docs/COREWEAVE.md for the exact verification boundary and historical benchmark limitations.
- Do not run concurrent experimental loops: they share harness/skills_overlay.json. Do not describe the repeatedly inspected CFO demo dataset as an untouched lockbox.
