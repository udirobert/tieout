# harness — tieout pipeline

`classify -> (sheet: codegen | cell: values-first) -> exec/write -> sanity + optional soffice -> repair <=3 -> fallback -> never blank`

Current brief: `docs/TEAM-BRIEF.md`. Methodology: `research/methodology-notes.md`.
Tinker Qwen3.8-27B is the default. Thinking off, 16k output tokens, temperature 0.

```
python harness/pipeline.py --dataset-dir /data --out-dir /out
python harness/pipeline.py --dataset-dir ... --out-dir ... --ids 13-1,51-12 --fresh
```

`--resume` (default) skips ids already in `predictions.jsonl`. `--fresh` wipes the out-dir artifacts first.
`--path hybrid` (default, ship): cell values-only, sheet codegen-only.
Sheet codegen + LibreOffice `#ERR!` → values-first (C recalc-as-gate).
Pinned answer range is coordinates only (no init values — models were echoing them).
`--path auto` adds one cross-path fallback. `--temperature` (default 0; B uses 0.7).

## Files

- `pipeline.py` — entry. Sheet-level: codegen loop then one values-first fallback. Cell-level: values-first then one codegen fallback. Default `--model tinker:Qwen/Qwen3.8-27B`.
- `adapters.py` — `tinker:<base>|<model_path>` primary; `gemini:<model>` spare. No OpenRouter.
- `prompts.py` — `SYSTEM_VALUES` / `CODEGEN_SYSTEM` + attribution-guided repair prompts.
- `executor.py` — subprocess sandbox in a temp dir (init copied in; goldens not visible). Import allowlist, timeout 120s, API keys stripped.
- `serializer.py` — 120×30 preview + fill-aware lines + pinned answer-range excerpt (survives the 20k cut).
- `parsing.py` — lenient JSON (keeps `Sheet1!B6`) and codegen fence parser.
- `verifier.py` — graded cells present + scalars + no `#ERR!`; soffice recalc when `SOFFICE` / LibreOffice exists, silent skip otherwise.
- `tracer.py` — `traces/<id>.jsonl`, one line per model call. Codegen steps add `tool`/`tool_output`.

Greedy decode / temperature 0. Keys via env only (`TINKER_API_KEY`, optional `GEMINI_API_KEY`).
