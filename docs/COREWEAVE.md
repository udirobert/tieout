# tieout — CoreWeave Hacks

**Every cell tied to its source — and now the agent learns from the ones it misses.**

## What was built this weekend (the judged delta)

The reconciliation engine (verify → repair → exception queue → human review)
was built at a previous hackathon and is disclosed prior work. What it lacked
was learning: every failed cell, repair trace, and exception was a dead-end
artifact. This weekend we closed the loop:

```
run pipeline on eval split
  → golden scorer (cell-level exact match, no LLM judge)
  → cluster failures by signature
  → mutator agent rewrites the agent's own skill library
  → re-score → keep on strict improvement, revert on regression
  → one final score on a lockbox set the mutator never saw
```

The mutation surface is `harness/skills_overlay.json` — domain skill fragments
the agent injects into its own code-generation prompt, gated by keyword match
on the task instruction. Learned skills must be keyword-gated and ≤1500 chars
(prompt-bloat / negative-transfer guards); a mutation can also `replace` a base
skill. Keep/revert is hill-climbing on `cell_accuracy` over a fixed eval split
at temperature 0 — paired comparison, not independent samples.

**Lockbox:** `demo/close-tieout` (CFO fund-admin tasks, a different
distribution than the dev set) is scored once after selection — proof the
learned skills transfer rather than memorize.

## Sponsor tools

| Tool | Use |
|------|-----|
| **W&B Serverless Inference** | Runtime model + mutator (`wandb:` adapter; OpenAI-compatible, `chat_template_kwargs` for thinking control) |
| **Weave** | `weave.op` tracing of every model call / verify / repair; `weave.Evaluation` per loop iteration; eval history is the improvement curve |
| **marimo** | `demo/loop_dashboard.py` — accuracy curve + exception-queue review UI |
| **W&B MCP** | optional — query runs/traces from the coding agent |

## Architecture

```
harness/pipeline.py     classify → values|codegen → verify → repair ≤3 → exceptions
harness/skills.py       base fragments + skills_overlay.json (the learned library)
harness/adapters.py     tinker: | gemini: | wandb: (W&B Inference)
harness/weave_hooks.py  lazy weave.init + call-time op wrappers (no-op offline)
research/weave_eval.py  TieoutModel(weave.Model) + cell_score(weave scorer)
research/loop.py        the self-improvement driver (this weekend's core)
demo/loop_dashboard.py  marimo panel
scripts/sweep.sh        model × path factorial sweep
```

## Commands

```bash
export WANDB_API_KEY=...   # enables Inference + Weave

# factorial config sweep (~2 min/cell at 15 tasks)
./scripts/sweep.sh research/data/spreadsheetbench_verified_400 15

# the loop: dev set for mutation+selection, CFO set as lockbox
cd research && uv run python loop.py \
  --dataset-dir data/spreadsheetbench_verified_400 --sample 20 --iters 3 \
  --model wandb:meta-llama/Llama-3.3-70B-Instruct \
  --holdout-dir ../demo/close-tieout --out-dir /tmp/tieout-loop

# dashboard
uv run marimo run ../demo/loop_dashboard.py
```

## Methodology guards (from published prompt-optimization work)

- Mutation and selection share the dev split; the lockbox is scored once, never
  shown to the mutator.
- Paired, same-task, temp-0 scoring — deltas are signal, not seed noise.
- Ties keep the incumbent; >10pt single-mutation gains are flagged for audit.
- Learned skills: keyword-gated, ≤1500 chars, ≤3 per iteration.
- Mutator sees failure signatures and instructions — the skills it writes are
  task-generic.
