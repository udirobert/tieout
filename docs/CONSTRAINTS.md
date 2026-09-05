# Constraints — space-constrained Mac, external services only

## 0. Iron rule

Ask before anything that uses disk. This Mac is space-constrained.
Text scaffolding (KBs) is fine. Anything below is VENUE-ONLY.

Do NOT run on this Mac before the venue:
- `uv sync` (~300–500MB)
- `research/data/download.py` (15MB tarball — tiny but skip for now)
- `brew install --cask libreoffice` (~1GB+, scorer recalc only)
- `docker build / docker run` (GBs)
- Any local Qwen weights or HF downloads

`tieout/` is currently ~780K (scaffolding only). Keep it that way until venue wifi.

## 1. Model / compute credits (provided at team-forming)

- Model credits for building — issued to every team at team-forming. Ask at the desk if burned through.
- API keys — one per team. NEVER commit to public repo. Name them in SUBMISSION.md only.
  Use env vars (`TINKER_API_KEY`, `GEMINI_API_KEY`, etc. via `.env`, gitignored).
- Qwen3.8-27B — fixed model everyone builds on. Hosted/provided, not supplied locally.
  Baselines (one-shot, values not formulas, all 400): DeepSeek-V3.2 55.8%, Qwen3.8-27B 59.0%, Gemini 3.7 Flash 68.3%.
  59.0% is our floor — edge comes from harness + fine-tune, not model size.
- Inference decision (Sat 12:45): OpenRouter is SKIPPED (personal key unfunded, team credits
  may be an OpenRouter promo — grab at desk as warm spare only). Primary inference is the
  free GEMINI_API_KEY from AI Studio on the hackathon gcplab project (Gemini 3.7 Flash was the
  strongest baseline at 68.3%); Tinker is the fine-tune + checkpoint path. Harness complete()
  adapters: gemini (primary) + tinker (finetune). Container `-e` contract: GEMINI_API_KEY and/or
  TINKER_API_KEY only — no OPENROUTER anywhere in the shipped image.
- gcplab environment (accounts/projects/keys) is decommissioned Sunday — never commit keys;
  SUBMISSION.md lists env names only.

## 2. Research-track specifics

- Tinker (Thinking Machines Lab) access — for fine-tuning. Invite-only after team forms + picks research track.
  Sign-in via Google. Invites sent manually — queue early.
- Google Cloud account — one per member, needed to unlock Tinker invite.
  Use a personally-controlled account (locked-down work accounts fail).
  Give address to research desk at team-forming. Do not wait until training time.
- Working repo to start from — `research/` in this repo (uv + 400 tasks pre-fetched at venue).
- One-shot baseline + official scorer (`research/evaluate.py`) — same scorer judges run. Self-evaluate identically.
- Reference Dockerfile — submission container. Judges mount dataset read-only at `/data`, take `/out`.
  Required in `/out`: `predictions.jsonl`, `outputs/`, `traces/`, `run.log`.
  Model-written code must run INSIDE the container. Container that doesn't start unattended = 0.

## 3. Scoring (what matters)

- `pass_rate` (primary) — all 400 must be present, missing = fail. Never skip IDs.
- `cell_accuracy` (tie-break) + per-type pass rate (275 cell-level / 125 sheet-level).
- Held-back private real-fund dataset — overfit to the 400 gets exposed. Reward generalization.
- Write-up quality — approach + results judged together.

## 4. General / logistics

- Venue: Encode Hub, Shoreditch — wifi, power, food on site.
- Data pack & interviews: Discord (product track, check for overlap).
- Mentors: Ylookup engineers all weekend; real fund manager Sat afternoon; Encode desk for logistics.
- Guest talk: Simon Guo (Thinking Machines Lab) demoing Tinker.
- Guest talk + fund-manager interviews are the only scheduled learning — rest is build time.
