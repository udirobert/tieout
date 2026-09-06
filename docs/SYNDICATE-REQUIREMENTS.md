# Syndicate requirements checklist

**Deadline:** Sunday 6 September 2026, **23:00 GMT+1** (18:00 EDT)  
**Devpost:** https://syndicate-by-maximor.devpost.com/  
**Discord (mandatory):** https://discord.gg/Sy3EwRBQX3

Track: **Autonomous Office of the CFO** · Project: **tieout**

---

## Judging weights (align submission to these)

| Criterion | Weight | How tieout addresses it |
|-----------|--------|-------------------------|
| **AO usage & build process** | 25% | AO orchestrator + workers build Syndicate pivot; dashboard + session count in video — see `docs/SYNDICATE-AO-INTEGRATION.md` |
| **Technical execution & reliability** | 25% | Harness verify + retry; never-blank; traces; 68% eval suite validation |
| **Track fit & real-world value** | 25% | Ylookup anonymised GL/bank datasets; CFO workflows in `SYNDICATE-WORKFLOW.md` |
| **Demo & usability** | 15% | 3-min video, `demo/run_demo.sh`, exception queue with evidence |
| **Innovation** | 10% | Skills-from-failure loop without retraining; config-parity harness insight |

---

## Mandatory submission items

- [ ] **Track selected:** Autonomous Office of the CFO
- [ ] **Problem + target users** — `SYNDICATE.md` (fund accountants, month-end close)
- [ ] **Working project built during hackathon** — Syndicate pivot via AO (see disqualification note below)
- [ ] **GitHub repo** with setup instructions — `README.md`, `demo/run_demo.sh`
- [ ] **Demo video (3–5 min)** — must show:
  - [ ] End-to-end product workflow
  - [ ] **How AO was used to build the project**
  - [ ] **AO sessions involved**
  - [ ] **AO dashboard with total session count**
  - [ ] Evaluation / debugging / improvement process
- [ ] **Architecture + tools + eval method** — `SYNDICATE.md`, `harness/README.md`
- [ ] **Measurable results** — eval suite 68%; demo fixture pass; skill-improvement before/after
- [ ] **All team member names** on Devpost
- [ ] **One Devpost submission per team**
- [ ] **Every team member registered individually**
- [ ] **Hackathon pass** posted on X/LinkedIn tagging AO

---

## AO requirement (disqualification risk)

> Projects started before the hackathon or without meaningful AO usage will be disqualified.

**Mitigation:**
1. All **Syndicate-specific** work (fixtures, CFO docs, exception UX, demo video script) must go through **AO sessions** from now until submission.
2. Demo video must show **AO dashboard + total session count** (judges explicitly check this).
3. Devpost write-up: separate **Encode archive** (`SUBMISSION.md`) from **AO-built Syndicate pivot** (`SYNDICATE.md`).
4. Log every AO session in `docs/SYNDICATE-DEMO.md` AO table.

**Do not claim** the entire Encode weekend was built in AO if it wasn't — frame honestly:
*"Encode validated the harness; Syndicate pivot (CFO demo, fixtures, exception workflow) built with AO."*

---

## Space budget (this Mac — ~31 GB free)

| Action | Disk impact | Status |
|--------|-------------|--------|
| Demo fixtures (`demo/build_fixtures.py`) | **~44 KB** | Done |
| Syndicate docs | **< 100 KB** | Done |
| AO desktop install | **~500 MB** | Pending |
| Demo video render | **50–200 MB** | OK; delete intermediates after |
| `uv sync` / venv | **300–500 MB** | Done (`cd research && uv sync`) |
| Copy full Ylookup datasets (17 MB) | 17 MB | **Not needed** — fixtures extracted |
| `docker build` | **10+ GB** | **Do not run on this Mac** — use VM or skip for Syndicate |
| LibreOffice install | **~1 GB** | Skip locally; optional on VM |
| LoRA / local weights | **GB+** | Not needed for Syndicate demo |

**Rule:** If any step needs **> 500 MB** beyond AO + video, stop and discuss VM/cloud options first.

---

## Inference & credits

### Tinker (Thinking Machines)

Required for live agent demo runs (`TINKER_API_KEY`).

**Before running pipeline on demo fixtures:**
1. Log in to Tinker dashboard / billing for your project
2. Confirm credits remain for ~3–5 demo tasks (not full 400)
3. Smoke test: `./demo/simulate_demo.sh close-tieout-bank-cp` (free) or `./demo/run_demo.sh close-tieout-bank-cp` (~30–60s live)

If credits exhausted: demo video can show **fixture walkthrough + trace format** without live inference, but live run is stronger for judges.

### Alternatives (no gcloud VM)

Previous gcloud VM is unavailable. Options if heavy compute needed:

| Option | Use for | Notes |
|--------|---------|-------|
| **This Mac** | Fixtures, docs, video, single-task Tinker demo | Space-limited |
| **TensorMux** (hackathon inference partner) | Ask in Discord | Sponsor-supported |
| **New cloud VM** (AWS/GCP/Azure/Hetzner) | Docker full-400, LibreOffice recalc | Only if needed; not for Syndicate demo |
| **Gemini spare** (`GEMINI_API_KEY`) | Fallback adapter in harness | Already wired |

---

## Demo fixtures (Ylookup datasets)

Built from anonymised client data in Downloads — **not copied wholesale**:

```bash
python3 demo/build_fixtures.py          # ~44 KB into demo/close-tieout/
./demo/simulate_demo.sh close-tieout-bank-cp   # offline smoke (no TINKER_API_KEY)
```

| Task ID | CFO workflow | Source | Demo role |
|---------|--------------|--------|-----------|
| **`close-tieout-bank-cp`** | **Bank counterparty match** | Dataset 01 Staging Sheet | **Hero — record this** |
| `close-tieout-le-map` | Entity mapping (GL migration) | Dataset 02 LE Mapping | Skill demo beat |
| `close-tieout-movements-rec` | Pre-upload reconciliation | Dataset 02 Movements Rec | Secondary (11 EXCEPTION sentinels) |

Known unmatched rows in source data are **preserved by design** — they feed the exception-queue story.

---

## Pre-submit final check (23:00 deadline)

1. `python3 demo/build_fixtures.py` — fixtures present
2. `./demo/simulate_demo.sh close-tieout-bank-cp` — exceptions.json + trace OK
3. Optional: `./demo/run_demo.sh close-tieout-bank-cp` with `TINKER_API_KEY`
4. Demo video uploaded (≤5 min, shows AO dashboard)
5. Devpost submitted with track, repo, video, AO explanation
6. Discord announcement / pass posted
