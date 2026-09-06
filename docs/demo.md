# Demo — script, commands, recording

**Hero fixture:** `close-tieout-bank-cp` (bank counterparty match)  
**Duration:** ≤4 min (aim 3:30) · **Mandatory:** AO dashboard with **total session count**

Real fund-admin data → agent proposes → exceptions with evidence → human approves → built with AO.

---

## Wedge

> Verification-first — never silent commit. Unmatched rows route to humans with evidence.
> Every cell tied to its source.

Deliberate unmatched rows in the source data are **by design** — they feed the exception queue.

---

## Story spine

| Time | Beat | Command / visual |
|------|------|------------------|
| 0:00–0:25 | Hook | NAV / close pain — Excel still runs month-end |
| 0:25–0:45 | Scenario | Open bank-cp workbook — cols J/K, vendor master |
| 0:45–1:25 | Agent run | `./demo/simulate_demo.sh close-tieout-bank-cp` |
| 1:25–1:50 | Exceptions | `cat /tmp/syndicate-demo/exceptions.json` |
| 1:50–2:20 | Human review | `uv run python ../harness/exceptions.py review …` |
| 2:20–2:40 | Skill loop | `./demo/run_skill_demo.sh` *(optional)* |
| 2:40–3:00 | AO | Dashboard — session count visible |
| 3:00–3:15 | Close | Tagline |

---

## Commands

```bash
python3 demo/build_fixtures.py
./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden
cat /tmp/syndicate-demo/exceptions.json
cd research && uv run python ../harness/exceptions.py review /tmp/syndicate-demo/exceptions.json
./demo/run_skill_demo.sh
# optional live — set TINKER_API_KEY from .env first
./demo/run_demo.sh close-tieout-bank-cp
```

---

## Show vs skip

| Show | Skip |
|------|------|
| bank-cp + 2 exceptions | Bulk eval runs |
| Approve + reject in review CLI | Auth, Docker, infra |
| AO dashboard + session count | Deep dive on all 3 fixtures |

---

## Recording

QuickTime or OBS · large terminal font · `tieout-syndicate-demo.mp4`

```bash
rm -rf /tmp/syndicate-demo && clear
```

Open AO with session count ready for the 2:40 beat.

**Shot 3** — expect `Exceptions: 2`:

```bash
./demo/simulate_demo.sh close-tieout-bank-cp /tmp/syndicate-demo golden
```

**Shot 5** — approve one exception (`y`), reject one (`n`).

**Post-production:**
- [ ] 3–5 min, AO count visible ≥5 sec
- [ ] URL in [submit.md](submit.md)
