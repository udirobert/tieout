# Final Shot-by-Shot Video Script — tieout Syndicate Demo

**Hero fixture:** `close-tieout-bank-cp` (bank counterparty match)  
**Target duration:** ≤ 4 minutes (aim 3:30)  
**Format:** 1080p screen recording, large terminal font, no background music required

---

## Shot 1 — Hook (0:00–0:25)

| Field | Content |
|-------|---------|
| Time | 0:00–0:25 |
| Visual | Terminal prompt, static; optionally a brief flash of an Excel workbook packed with columns J/K and a vendor-master tab |
| Action | Type the clean-up command, then pause before the next line. |
| Narration | "Month-end close in private markets still runs in Excel. Tying out bank counterparties, matching names and amounts, chasing the one row that doesn't belong — it's repetitive, error-prone, and worst of all, silent. One wrong cell gets copied forward and nobody notices." |
| Notes | Keep text minimal on screen. Let the terminal dominate. |

---

## Shot 2 — The Scenario (0:25–0:45)

| Field | Content |
|-------|---------|
| Time | 0:25–0:45 |
| Visual | Open `demo/close-tieout/` workbook or `cat` the fixture summary. Show the bank-cp source columns and the vendor master side-by-side. |
| Action | Scroll once or run `python3 demo/build_fixtures.py` to show fixtures being built. |
| Narration | "Here's a real-shaped fund-admin scenario: a bank counterparty tie-out. We have cash activity in column J, GL entries in column K, and a vendor master on the side. Two rows are deliberately unmatched — they're the exceptions we want the agent to surface, not hide." |
| Notes | Emphasize that deliberate mismatches are by design. |

---

## Shot 3 — Agent Run (0:45–1:25)

| Field | Content |
|-------|---------|
| Time | 0:45–1:25 |
| Visual | Full terminal. Run the hero fixture command end-to-end. |
| Command | `./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden` |
| Action | Let it run; output should end with `Exceptions: 2` and a `trace/` directory. |
| Narration | "We hand tieout a mandate and the workbook. It classifies the task, executes the transform, verifies every answer cell, and retries with attribution when something breaks. When a row can't be matched, it stops and emits evidence — never a silent commit." |
| Notes | Wait for the prompt to return; do not cut early. |

---

## Shot 4 — Exceptions (1:25–1:50)

| Field | Content |
|-------|---------|
| Time | 1:25–1:50 |
| Visual | `cat /tmp/syndicate-demo/exceptions.json` in terminal. |
| Action | Pipe to `jq` for readability or `cat` the raw JSON. |
| Narration | "The exception queue is a first-class artifact. Each item points back to the source rows, the proposed match, and why the agent isn't confident. The human doesn't have to reverse-engineer anything." |
| Notes | Zoom in enough to show the `row_id` and `reason` fields clearly. |

---

## Shot 5 — Human Review (1:50–2:20)

| Field | Content |
|-------|---------|
| Time | 1:50–2:20 |
| Visual | Review CLI prompt inside `research/`. |
| Command | `uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json` |
| Action | Approve the first exception with `y`, reject the second with `n`. |
| Narration | "A human reviews the queue. Approve one, reject the other. The rejected row goes back for another pass or manual handling; the approved one is accepted into the final workbook. Verification first, human in the loop, source attribution all the way down." |
| Notes | Keep keystrokes visible. Show the `y` and `n` responses. |

---

## Shot 6 — AO Dashboard (2:20–2:50)

| Field | Content |
|-------|---------|
| Time | 2:20–2:50 |
| Visual | Agent Orchestrator desktop app: project view open, session list visible, total session count clearly readable. |
| Action | Run `ao session ls` or scroll the dashboard; hold the total count on screen for at least 5 seconds. |
| Narration | "This wasn't built in one terminal. Agent Orchestrator supervised focused worker sessions: exception queue, demo fixtures, docs, and this video script. The dashboard shows the total session count, and every run left a trace in git." |
| Notes | Mandatory judging requirement: AO dashboard + total session count visible for ≥ 5 sec. |

---

## Shot 7 — Close / Tagline (2:50–3:15)

| Field | Content |
|-------|---------|
| Time | 2:50–3:15 |
| Visual | Terminal clears to a static final frame or back to the prompt with the project name. |
| Action | Type nothing; hold the final command or README first line. |
| Narration | "tieout: every cell tied to its source. Autonomous spreadsheet reconciliation for finance close — verification-first, human-approved, fully auditable." |
| Notes | End on the tagline. Keep on screen for 5 seconds. |

---

## Recording Checklist

- [ ] Reset demo state: `rm -rf /tmp/syndicate-demo && clear`
- [ ] Record at large terminal font (≥ 14 pt)
- [ ] Shot 3 confirms `Exceptions: 2`
- [ ] Shot 5 shows one `y` and one `n`
- [ ] Shot 6 holds AO dashboard session count for ≥ 5 seconds
- [ ] Final output file: `tieout-syndicate-demo.mp4`
- [ ] Duration trimmed to 3:00–3:30

---

## Voiceover Notes

Speak calmly and avoid filler. Total narration should fit the target duration with pauses left for command output. If running over, trim Shot 6 to the minimum 5-second hold.
