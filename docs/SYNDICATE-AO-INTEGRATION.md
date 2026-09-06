# AO integration plan — Syndicate submission

**AO:** [aoagents.dev](https://aoagents.dev/) · [GitHub](https://github.com/Untrivial-ai/agent-orchestrator)  
**Judging:** AO Usage & Build Process = **25%** · Demo must show **AO dashboard + total session count**

---

## What AO is (and is not)

| AO **is** | AO **is not** |
|-----------|----------------|
| Desktop IDE to **supervise coding agents** building your repo | The runtime that executes tieout on spreadsheets |
| Orchestrator + workers in **isolated git worktrees** | A replacement for Tinker/Gemini at inference time |
| Kanban for sessions, PRs, CI, review feedback | Something you embed inside `harness/pipeline.py` |

**Correct integration model:**

```
┌─────────────────────────────────────────────────────────────┐
│  AO (Agent Orchestrator)                                     │
│  Orchestrator session → plans Syndicate pivot                │
│  Worker sessions → implement code/docs in tieout repo        │
│       │                                                      │
│       ▼                                                      │
│  tieout repo (harness/, demo/, docs/)                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼  (separate — inference)
              Tinker Qwen3.8-27B / Gemini
              runs harness/pipeline.py on CFO demo fixtures
```

Judges want evidence that **AO coordinated the build**. The demo video shows:
1. **tieout product** — finance close agent on Ylookup fixtures
2. **AO dashboard** — session list/count from building the Syndicate pivot

Do **not** claim Encode weekend work was AO-built unless it was. Frame honestly:

> Encode validated the spreadsheet harness (Sept 5–6). Syndicate pivot — CFO demo,
> Ylookup fixtures, exception workflow, submission docs — built with AO workers
> during the hackathon window.

---

## Install (not yet on this Mac)

AO is **not installed** here (`~/.ao` absent, no desktop app found).

### Recommended path — desktop app (canonical)

1. Download **macOS Apple silicon** DMG:  
   https://github.com/Untrivial-ai/agent-orchestrator/releases/latest/download/agent-orchestrator-darwin-arm64.dmg
2. Install and open **Agent Orchestrator** (starts local daemon on `127.0.0.1:3001`, data in `~/.ao/`)
3. **Disk warning:** app + daemon + worktrees ≈ **300–800 MB** base, **+~200 MB per active worker worktree**. With **~31 GB free**, cap at **2–3 concurrent workers**; merge/archive sessions promptly.

### Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| Git | yes | Already have (tieout repo) |
| GitHub CLI `gh` | recommended | `gh auth login` — for PR workflow if workers open PRs |
| Agent harness | yes | **Cursor** (supported) or Claude Code / Codex / OpenCode |
| tmux | yes on macOS | Terminal UI sessions; Chat mode may not need it |

Legacy npm CLI (`@aoagents/ao@0.10.0`) is **frozen** — use desktop app, not npm.

### Optional CLI (after desktop app running)

```bash
ao doctor          # git, tmux, agent harness checks
ao status
ao session ls      # session count for demo video
ao project ls
```

---

## Step 1 — Register tieout as an AO project (~10 min)

1. Open AO desktop → **Add project** → select `/Users/udingethe/Dev/tieout`
2. Project settings:
   - **Worker agent:** Cursor (or Claude Code / Codex if preferred)
   - **Orchestrator agent:** same or stronger model for planning
3. Add project rules (paste into worker `agentRules` or project config):

```markdown
## tieout — Syndicate Track 2 (Office of the CFO)

Read before any task:
- SYNDICATE.md
- docs/SYNDICATE-WORKFLOW.md
- docs/SYNDICATE-REQUIREMENTS.md
- docs/SYNDICATE-AO-INTEGRATION.md (this file)

Constraints:
- Space-constrained Mac (~31 GB free). No docker build, no large downloads.
- Demo fixtures in demo/close-tieout/ (~44 KB). Rebuild: python3 demo/build_fixtures.py
- Hero demo: close-tieout-bank-cp — see docs/SYNDICATE-DEMO.md
- Local runs: cd research && uv run python ../harness/...
- Do not modify research/ (upstream read-only).
- Harness entry for demo: harness/pipeline.py --path hybrid (not clone_run.py).
- Tinker inference only for live demo runs; check credits before batch runs.

Track 2 focus: finance close workflows, exception queue, human review — not SpreadsheetBench scores.
```

4. Orchestrator rules (`orchestratorRules`):

```markdown
You supervise tieout's Syndicate submission. Break work into focused worker tasks.
Each worker owns one outcome (one file or one feature). Prefer 2–3 parallel workers max
(disk limit). Update docs/SYNDICATE-DEMO.md AO session table when spawning workers.
```

---

## Step 2 — Orchestrator plans remaining work (~15 min)

Start **one orchestrator session** (Chat recommended):

```bash
# CLI alternative (daemon must be running via desktop app):
ao spawn --project tieout --kind orchestrator --name syndicate-plan --mode chat
```

**Orchestrator prompt (paste):**

```
Syndicate hackathon deadline: ~5 hours. Track 2 — Autonomous Office of the CFO.

Repo: tieout — spreadsheet reconciliation agent for finance close.
Done: SYNDICATE.md, demo fixtures (demo/close-tieout/, 3 tasks), build_fixtures.py.
Pending: harness/exceptions.py, wire exceptions into pipeline, one skill-improvement demo,
3–5 min demo video script, Devpost submission.

Read SYNDICATE.md and docs/SYNDICATE-REQUIREMENTS.md. Produce a task breakdown and spawn
focused workers. Max 3 parallel workers (disk constraint). Each worker gets a clear
acceptance criterion and must not touch unrelated files.
```

---

## Step 3 — Worker sessions for Syndicate pivot (~3–4 hrs)

Spawn **separate worker sessions** (each = one AO session on the dashboard). Suggested split:

| # | Worker name | Task | Acceptance | Branch |
|---|-------------|------|------------|--------|
| 1 | `exceptions` | `harness/exceptions.py` + pipeline hook on verify fail | Writes `exceptions.json` with evidence rows; `demo/run_demo.sh` documents review | `syndicate/exceptions` |
| 2 | `ao-docs` | Update `docs/SYNDICATE-DEMO.md` AO table; add `docs/AO-SESSION-LOG.md` | Every session id + purpose logged | `syndicate/ao-log` |
| 3 | `demo-polish` | README setup for AO; `.ao/launch.json` optional for `ao preview` | `./demo/run_demo.sh` works; no docker | `syndicate/demo` |
| 4 | `skill-demo` | One before/after skill injection script or doc in `demo/` | Documented in SYNDICATE-DEMO beat 2:20–2:45 | `syndicate/skills` |

**Spawn example (CLI):**

```bash
ao spawn --project tieout --kind worker --name exceptions --mode chat \
  --prompt "Implement harness/exceptions.py: on verifier failure, append to exceptions.json with task_id, cell, reason, evidence_rows. Wire into harness/pipeline.py after sanity_check fails. Read docs/SYNDICATE-WORKFLOW.md human review section. Minimal diff. Run no docker."
```

**Cursor in AO:** Select **Cursor** harness when creating the worker in the desktop UI if CLI spawn doesn't expose it — AO supports Cursor natively.

Each completed worker → merge to `main` (or single integration branch) → **session stays visible** on Kanban for demo footage.

---

## Step 4 — Record AO evidence for judges (~30 min)

Devpost requires demo video to show:

- [ ] **AO dashboard** with project + sessions visible
- [ ] **Total session count** (sidebar or `ao session ls | wc -l`)
- [ ] At least one **worker session** mid-build (Chat or terminal showing task prompt)
- [ ] **Orchestrator** delegating (optional but strong for 25% criterion)
- [ ] tieout **product demo** (separate segment — `./demo/run_demo.sh` or live Tinker run)

Suggested video structure (5 min max) — **canonical script:** `docs/SYNDICATE-DEMO.md`

| Time | Content |
|------|---------|
| 0:00–0:25 | Hook (call-1 NAV pain) + tieout one-liner |
| 0:25–1:25 | Product: `./demo/simulate_demo.sh close-tieout-bank-cp` |
| 1:25–2:20 | Exception queue + human review CLI |
| 2:20–2:40 | Skill demo (`./demo/run_skill_demo.sh`) — optional |
| 2:40–3:00 | **AO dashboard — scroll sessions, show count** |
| 3:00–3:30 | Close + Devpost CTA |

Screenshot checklist before recording:

```bash
ao session ls          # count lines
ao status              # daemon healthy
```

---

## Step 5 — Devpost "How we used AO" (copy-ready draft)

> We used Agent Orchestrator (AO) as the development control plane for tieout's Syndicate
> pivot. An orchestrator session broke the remaining work into focused tasks; **N worker
> sessions** (Cursor/Claude) implemented the exception queue, Ylookup demo fixtures,
> and submission docs in isolated git worktrees. AO's Kanban tracked each session from
> task → implementation → merge. The spreadsheet agent itself runs via Tinker at inference
> time; AO orchestrated the **engineering** of that agent for Track 2 (Office of the CFO).
> Demo video shows the AO dashboard with total session count and one worker session recording.

Replace **N** with actual count from `ao session ls`.

---

## Space & infrastructure guardrails

| Action | Disk | Proceed? |
|--------|------|----------|
| Install AO desktop | ~300–500 MB | **Ask user first** — tight but OK |
| Each worker worktree | ~50–200 MB | Max 2–3 concurrent |
| `demo/build_fixtures.py` | 44 KB | ✅ Done |
| Live Tinker demo (3 tasks) | negligible | Check **Tinker credits** first |
| `docker build` | 10+ GB | ❌ Do not run on this Mac |
| Full SpreadsheetBench re-run | VM + dataset | ❌ Use archived eval only |

**No gcloud VM:** inference smoke tests run locally with Tinker API; heavy eval deferred.

**Tinker credits check:** log into Thinking Machines / Tinker dashboard before any live demo run. One fixture ≈ one API call (~30–60s). Budget 5–10 calls for demo + debugging.

**TensorMux:** ask Discord if Tinker credits are low — hackathon inference partner.

---

## tieout ↔ AO ↔ product mapping (judge narrative)

| Layer | Tool | What judges see |
|-------|------|-----------------|
| **Build** | AO orchestrator + workers | Dashboard, session count, PRs/commits |
| **Product** | tieout harness | CFO spreadsheet reconciliation |
| **Data** | Ylookup anonymised datasets | Real fund-admin workflows |
| **Validation** | SpreadsheetBench 400 (background) | 68% pass rate in write-up |
| **Debug** | Neatlogs (optional) | Trace inspection in demo |
| **Inference** | Tinker Qwen3.8-27B | Live demo run |

---

## Immediate next actions (ordered)

1. **Confirm disk OK** for AO desktop install (~500 MB)
2. **Install AO** + `gh auth status` + confirm Cursor harness detected (`ao doctor`)
3. **Add tieout project** + paste agent/orchestrator rules above
4. **Start orchestrator session** → spawn 3–4 workers for pending checklist items
5. **Log sessions** in `docs/SYNDICATE-DEMO.md` AO table as you go
6. **Check Tinker credits** before recording live inference
7. **Record demo video** with AO dashboard segment
8. **Submit Devpost** before 23:00 GMT+1

---

## References

- [AO docs](https://aoagents.dev/docs)
- [Installation](https://aoagents.dev/docs/installation)
- [Quickstart](https://aoagents.dev/docs/quickstart)
- [Per-role agents (orchestrator vs worker)](https://aoagents.dev/docs/guides/per-role-agents)
- [CLI reference](https://github.com/Untrivial-ai/agent-orchestrator/blob/main/docs/cli/README.md)
- [Syndicate pass](https://aoagents.dev/hackathons/syndicate/pass/)
- Internal: `docs/SYNDICATE-REQUIREMENTS.md`, `docs/SESSION-STATUS.md`
