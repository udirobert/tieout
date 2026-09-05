# LoRA v1 Failure Diagnosis & Evidence (Role C Archive)

## Summary of Run
- **Model**: LoRA checkpoint v1 on Qwen3.8-27B (trained on un-repaired 81 trajectories).
- **Evaluation Out-Dir**: `/tmp/tinker-400-lora` (preserved here in `research/data/eval/lora_v1/`).
- **Score**:
  - `pass_rate`: **0.3225** (129 / 400 passed)
  - `cell_accuracy`: **0.3592**
  - `cell_level`: **0.4655** (128 / 275 passed)
  - `sheet_level`: **0.0080** (1 / 125 passed)
  - `harness_status`: 272 ok / 8 partial / 120 errors (in `predictions.jsonl`)

## Root Cause Evidence
1. **Formatting & Syntax Drift**:
   - The un-repaired training set contained trailing punctuation, concatenated JSON blocks, and un-sanitized completions.
   - The model learned to emit corrupted JSON delimiters (e.g. `JSONDecodeError: Expecting ',' delimiter`), triggering 120 hard runtime parsing failures across the 400 evaluation set.
2. **Resolution Applied in v2**:
   - Built strict lossless round-trip validator (`research/validate_spans.py`).
   - Cleaned & frozen 228 balanced, verified trajectories under SHA-256 hash `3dae518df...`.
   - v2 training dataset guaranteed 100% parse-clean with zero empty completions or syntax leaks.
