# Results checklist — run at venue, paste into SUBMISSION.md

```sh
# subset iterate (no recalc, no LibreOffice needed)
uv run evaluate.py --predictions <out>/predictions.jsonl --no-recalc

# oracle must be 1.0
uv run evaluate.py --oracle

# official self-score (requires LibreOffice / SOFFICE for formula recalc)
uv run evaluate.py --predictions <out>/predictions.jsonl --all --out results.json
```

`results.json` summary block goes into SUBMISSION.md. `items` must be 400.
Reported scores decide run order only — judges' run ranks.

Pre-submit gates:
- [ ] predictions.jsonl has 400 lines, every `outputs/<id>.xlsx` exists + readable
- [ ] traces/<id>.jsonl one line per model call, failures kept with `error`, no golden values in prompts
- [ ] run.log is raw stdout/stderr, unedited
- [ ] Dockerfile builds + starts unattended: `docker run --rm -e <KEYS> -v <dataset>:/data:ro -v <empty>:/out tieout`
- [ ] No API keys in repo. Env names listed in SUBMISSION.md.
- [ ] `items: 400` in results.json summary
