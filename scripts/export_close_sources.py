#!/usr/bin/env python3
"""Export the close package's data sheets to CSV for Zetaris federation.

The wildcard demo reads the judgment queue through federated sources, not
files: the bank feed (bank-cp Staging Sheet), reference data (Corvus LE
Reference), and the GL (Movements Rec) each become a Lightning FILESTORE
table. This script writes one CSV per source to --out-dir; copy that
directory to the Zetaris host and register with zetaris/sql/.

    research/.venv/bin/python scripts/export_close_sources.py --out-dir /tmp/close-sources
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (source name, workbook, sheet, header row 1-based, data start row)
SOURCES = [
    (
        "bank_feed",
        "demo/close-tieout/spreadsheet/close-tieout-bank-cp/1_close-tieout-bank-cp_init.xlsx",
        "Staging Sheet",
        1,
        2,
    ),
    (
        "corvus_le_reference",
        "demo/close-tieout/spreadsheet/close-tieout-le-map/1_close-tieout-le-map_init.xlsx",
        "Corvus LE Reference",
        2,
        3,
    ),
    (
        "gl_movements",
        "demo/close-tieout/spreadsheet/close-tieout-movements-rec/1_close-tieout-movements-rec_init.xlsx",
        "Movements Rec",
        1,
        2,
    ),
]


def _col_name(raw, idx: int) -> str:
    name = str(raw).strip() if raw is not None else ""
    name = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower() or f"col_{idx}"
    return name


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()

    import openpyxl

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rel, sheet, header_row, data_start in SOURCES:
        wb = openpyxl.load_workbook(ROOT / rel, read_only=True)
        try:
            ws = wb[sheet]
            rows = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()
        headers = [_col_name(c, i + 1) for i, c in enumerate(rows[header_row - 1])]
        seen, cols = {}, []
        for h in headers:
            seen[h] = seen.get(h, 0) + 1
            cols.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
        out = args.out_dir / f"{name}.csv"
        n = 0
        with out.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for row in rows[data_start - 1 :]:
                if all(c is None for c in row):
                    continue
                w.writerow(list(row[: len(cols)]) + [None] * (len(cols) - len(row)))
                n += 1
        print(f"{name}: {n} rows -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
