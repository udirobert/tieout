"""Generate __marimo__/session/<demo>.json so the static preview shows the seeded story.

Skips when the seeded /tmp workspace already has a session file newer than the
notebook source — keeps the commit cheap on repeated CI runs. Not used at
runtime; only by maintainers regenerating the preview.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))
sys.path.insert(0, str(HERE.parent / "research"))

from marimo._cli.export.output import STDERR  # noqa: E402
from marimo._export.file import run_notebook  # noqa: E402
from marimo._export.requests import NotebookExecutionOptions, RunNotebookRequest  # noqa: E402
from marimo._server.utils import asyncio_run  # noqa: E402
from marimo._session.notebook import load_notebook  # noqa: E402
from marimo._session.state.serialize import (  # noqa: E402
    serialize_session_view,
)
from marimo._utils.inline_script_metadata import (  # noqa: E402
    script_metadata_hash_from_filename,
)
from marimo._export._session_cache import (  # noqa: E402
    write_session_snapshot,
    serialize_session_snapshot,
)


def main(seed_dir: Path) -> int:
    notebook = HERE / "demo_app.py"
    seed_dir.mkdir(parents=True, exist_ok=True)
    fm = load_notebook(notebook)
    view, _did_error = asyncio_run(
        run_notebook(
            RunNotebookRequest(
                file_manager=fm,
                options=NotebookExecutionOptions(
                    cli_args={},
                    argv=None,
                    stderr=STDERR,
                ),
            )
        )
    )
    cell_ids = list(fm.app.graph.cells.keys())
    snapshot = serialize_session_snapshot(
        view,
        notebook_path=notebook,
        cell_ids=cell_ids,
    )
    out = write_session_snapshot(notebook_path=notebook, snapshot=snapshot)
    print(f"wrote {out}  ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    seed_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/close-keeper-demo")
    sys.exit(main(seed_dir))
