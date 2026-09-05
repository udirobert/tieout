# Constraints — space-constrained Mac, external services only

> **Scoring + space rules below still apply.** Inference/role split was updated
> 2026-09-05: Qwen-only lifted, Tinker is primary, see `docs/TEAM-BRIEF.md`.
> Do not treat the Gemini-primary / OpenRouter notes in §1 as current.

## 0. Iron rule

Ask before anything that uses disk. This Mac is space-constrained.
Text scaffolding (KBs) is fine. Anything below is VENUE-ONLY.

Do NOT run on this Mac before the venue:
- `uv sync` (~300–500MB)
- `research/data/download.py` (15MB tarball — tiny but skip for now)
- `brew install --cask libreoffice` (~1GB+, scorer recalc only)
- `docker build / docker run` (GBs)
- Any local Qwen weights or HF downloads

Keep dataset downloads, LibreOffice, Docker, and local weights off this Mac
(`docs/SETUP.md` — those run on the VM). Do not `uv sync` here.

## 1. Model / compute credits (provided at team-forming)

- Model credits for building — issued to every team at team-forming. Ask at the desk if burned through.
- API keys — one per team. NEVER commit to public repo. Name them in SUBMISSION.md only.
  Use env vars (`TINKER_API_KEY`, `GEMINI_API_KEY`, etc. via `.env`, gitignored).
- Qwen3.8-27B — fixed model everyone builds on. Hosted/provided, not supplied locally.
  Baselines (one-shot, values not formulas, all 400): DeepSeek-V3.2 55.8%, Qwen3.8-27B 59.0%, Gemini 3.7 Flash 68.3%.
  59.0% is our floor — edge comes from harness + fine-tune, not model size.
- Inference (current): Tinker Qwen3.8-27B is primary (`TINKER_API_KEY`). Gemini 3.7 Flash
  is a spare teacher (`GEMINI_API_KEY`). OpenRouter is SKIPPED (unfunded) — no
  `OPENROUTER_API_KEY` in the shipped image. Container `-e` contract: `TINKER_API_KEY`
  and optionally `GEMINI_API_KEY`.
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
