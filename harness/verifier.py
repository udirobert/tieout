"""tieout verifier — second-derivation check before accepting a task.

Matches scorer normalization in research/sb.py: numbers rounded to 2dp,
dates as Excel serials, empty string equals empty cell (values_equal).
"""

# Venue implementation: load written workbook data_only=True + formula pass,
# compare derivation A (code-exec result) vs derivation B (re-read / pandas),
# return True only on AGREE. Disagreement -> retry (max 3), then best guess.

MAX_ATTEMPTS = 3
