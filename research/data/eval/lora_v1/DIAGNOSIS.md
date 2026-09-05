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

## 3. Step-200 Crashed-Run Diagnostic Evidence
- **Checkpoint URI**: `tinker://0c3c3765-2d63-5515-a49a-6613a7b9a888:train:0/sampler_weights/000200`
- **Subsample Evaluation**: Scored on the stratified 100-task benchmark (`research/data/subsample_100_ids.txt`, 50 cell / 50 sheet).
- **Finding**: Pre-fix syntax error emissions (e.g. `error: syntax error: invalid syntax (<unknown>, line 1)`) persisted across sheet codegen tasks, proving that the un-repaired delimiter drift was encoded into early weights and validating the need for the clean 60/40 mix SFT dataset (`build_sft_v2.py`).
