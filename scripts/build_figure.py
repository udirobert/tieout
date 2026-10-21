#!/usr/bin/env python3
"""Assemble docs/figures/index.html from the iso-glow template and Fig. 01.

The figure is a source file (`docs/figures/fig01-close-ledger.js`) plus the
iso-glow gallery template. This script joins them and applies the site's
design tokens, so the figure is native to the page rather than a second
design system.

Kept as a script rather than a hand-edited HTML file so the figure's source
stays readable and the tokens stay in one place.

Usage:
  python3 scripts/build_figure.py [--template PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path.home() / ".claude/skills/iso-glow/assets/gallery.html"
FIGURES = ROOT / "docs" / "figures"
TOKENS = ROOT / "docs" / "assets" / "tokens.css"


def dark_tokens() -> str:
    """The site's dark token block, in the gallery template's own layout."""
    text = TOKENS.read_text(encoding="utf-8")
    start = text.index(":root {")
    end = text.index("}", text.index("--serif:")) + 1
    block = text[start:end]
    # Re-wrap onto one line per group so the block reads like the template's
    # own, rather than as the source file's comment-laden version.
    lines = []
    group: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("/*") or line.startswith("*") or line.endswith("*/"):
            continue
        if line.startswith("--") and group:
            lines.append("  " + " ".join(group))
            group = []
        group.append(line)
    if group:
        lines.append("  " + " ".join(group))
    return "\n".join(lines)


def light_tokens() -> str:
    """The site's light-theme values, in the template's two light blocks."""
    values = (
        "    color-scheme: light;\n"
        "    --bg:#f5f2ec; --panel:#fffdf9; --edge:#dcd6ca;\n"
        "    --line:#8e887c; --detail:#cfc9bd; --body:#f0ece3; --deck:#ece7dd;\n"
        "    --ink:#5d574c; --ink-hi:#1b1a17; --live:#1b1a17;\n"
        "    --glass:#ffffff; --glass-on:#fbeadd; --recess:#e6e1d6;\n"
        "    --accent:#b4530f; --accent-hi:#8f3f08; --accent-dim:rgba(180,83,15,.08);\n"
    )
    return (
        '  @media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) {\n'
        + values
        + "  } }\n"
        + '  :root[data-theme="light"] {\n'
        + values
        + "  }"
    )


def build(template: Path, out: Path) -> None:
    figure = (FIGURES / "fig01-close-ledger.js").read_text(encoding="utf-8")
    html = template.read_text(encoding="utf-8")

    # Swap the template's palette for the site's tokens, dark and light.
    html = re.sub(
        r"  :root \{.*?\n  \}",
        dark_tokens(),
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"  @media \(prefers-color-scheme: light\).*?\n  \}\n",
        light_tokens() + "\n",
        html,
        count=1,
        flags=re.DOTALL,
    )

    for old, new in [
        ("<title>Iso Figures</title>", "<title>Fig 01 · The close ledger — tieout</title>"),
        ("Iso figures</span>", "The close ledger</span>"),
        # The palette picker offers the iso-glow defaults; the figure's own
        # palette is the site's accent, so "orange means live" holds across
        # both surfaces. The other swatches remain as an exploration, and the
        # stored choice is namespaced so it cannot leak into another gallery.
        (
            "window.GALLERY = { palette: 'ember', autoDemo: false, storageKey: 'iso-glow-accent' };",
            "window.GALLERY = { palette: [['Tieout','#e07a3a','#f0a878','#b4530f','#8f3f08'], "
            "['Ember','#ff7a1a','#ffb070','#f06a00','#ff8c2e'], "
            "['Cyan','#22d3ee','#9beefa','#0891b2','#06a8c6'], "
            "['Lime','#a3e635','#d6f79f','#4d7c0f','#5f960f']], "
            "autoDemo: false, storageKey: 'tieout-figure-accent' };",
        ),
        ("/* paste figure scripts here (see examples/) */", figure),
    ]:
        if old not in html:
            raise SystemExit(f"template marker missing: {old!r}")
        html = html.replace(old, new, 1)

    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(html):,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--template", default=str(TEMPLATE))
    parser.add_argument("--out", default=str(FIGURES / "index.html"))
    args = parser.parse_args()
    template = Path(args.template)
    if not template.exists():
        raise SystemExit(
            f"template not found: {template}\n"
            "install the iso-glow skill, or pass --template"
        )
    build(template, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
