---
workflow: general-video
flow: automation
storyboard: no
message: "The agent that won't write is the agent a fund can trust."
destination: hackathon-submission-video
aspect: 1920x1080
language: en
length: 120s
audience: "Judged by Seapoint (sponsor) and 13books Capital (seed investor); on screen the ICP is a founder or first finance hire at a 12-person venture-backed startup doing the close alone."
angle: problem-turn-stakes
---

## Intent

The submitted two-minute demo film for the FinOps Hackathon (20 Oct 2026), re-cut afterwards to
answer the judges' critique. Seven beats: someone has the problem alone at midnight → **the close
is six named steps and step three is where the guessing lives** → the books are read live → the
quiet work is what matters → it has to *earn* an answer before anything is written → the one
contradiction I'd show a partner → the stakes. Tone: quiet, precise, editorial. No talking head,
no music swell, no narration over the refusal. Motion doctrine inherited from `videos/tieout-demo`:
land, don't fade.

Delivered as `renders/close-keeper-finops-v6.mp4` (ignored; re-render with `npm run render` after
regenerating audio). v5 — the cut that was actually submitted — is superseded but its honesty rules
all carried forward.

## Assets

- `assets/footage/close-keeper-live-seapoint.mp4` — 13.4s, beat 3. Styled replay of the real
  20 Oct Seapoint MCP pull: spend by category, the 0.5% thesis, the judgment queue.
- `assets/footage/close-keeper-governed-refusal.mp4` — 17.0s, beat 5. Real local run, key-free,
  no model: two refusals, then an activation earned on 7 labeled replays.
- `assets/img/cap-queue.png` — crop of the live session's own `Why I won't code it` table
  ("Would refuse / route to you (10)"), beat 4. The 78MB source `.mov` lives on the Desktop,
  not in git; this crop is the durable copy.
- `assets/img/cap-writeback.png` — crop of the real ledger write-back gate for the Connolly
  transaction, beat 5.
- `assets/img/*.png` (ignored, regenerable) — risograph character cutouts via the ElevenLabs
  Images API, `model_id: gemini-3-pro-image`. Text-free by instruction, so nothing in the
  character layer reads as evidence.
- `assets/voice/00–06.mp3` (ignored, regenerable) — `scripts/build_audio.py`, ElevenLabs
  George / `eleven_multilingual_v2`. Measured durations (9.66 / 17.69 / 10.73 / 17.51 / 14.44 /
  17.23 / 17.83 = 105.1s of speech) drive every scene boundary; scene starts are
  0 / 11 / 30.5 / 42.5 / 61 / 81 / 99.5.
- `close_keeper/video-script.md` — the story spine and recording plan.

## Customizations

- Beat 2 lands one row per spoken step (1.3s apart), then reveals who owns which step: two green
  `Seapoint` tags, one orange `the judgment queue`, three grey `not ours` / `waits on a human`.
  The boundary is on screen, not in a disclaimer.
- Count-up on the 14 in beat 4; the stamp lands on the spoken "it won't write it" with a frame shake.
- Sentence-chunk captions timed to the measured VO, never two in the same band at once.
- BGM was attempted and abandoned — the ElevenLabs music endpoint 404'd, and the film works
  on narration alone. The silent holds are intentional, not unfinished.

## Notes

- **Outcome: did not place** (FinOps Hackathon, 20 Oct 2026). The judges' stated reason was that
  the entry didn't clearly show **a workflow people already do**, and how the agentic solution
  fixes or improves on it. That is a structural hit on the argument, not on the craft: v5's beat 2
  was a *query* ("what did we spend last month by category"), and a query is not a process — so the
  refusal never got a baseline to be better than. Fixed in v6 by beat 2 above, which is the same
  six rows as `close_keeper/README.md` → *The workflow this sits inside* and the site's `#workflow`
  section, in the same order, with the same ownership claims.
- Beat 2's provenance chip reads `described process · not a measurement`, and beat 1's reads
  `a frame, not a case study`. The film's green chips mean "this was counted"; the orange ones mean
  "this is a claim or a frame". Do not swap them, and do not let a future cut promote the six steps
  into a measured claim — no customer, no time-and-motion study.
- Honesty rules that survived to the final cut: no invented customer; no number spoken that is not
  on screen; every capture labelled with its provenance, including the Seapoint clip's
  "styled replay of the live pull".
- The live session disproved one earlier rule. close-keeper **does** write to Seapoint — via
  `set_transaction_coding`, held behind an explicit go-ahead, returning `change_id` audit
  records. The film says "nothing writes until you say so" rather than "it never writes".
- Two counts that must not be conflated: **14** is `needs_review 7 + unreconciled 7` from the
  distribution; **10** is what the agent said it would refuse to code. Beat 4 shows both,
  labelled, so the difference is on screen rather than a discrepancy a judge has to catch.
- Meridian Insurance was coded with a warning in the real run, not refused outright — the
  agent flagged "also recategorises from Legal & Professional Fees → Insurance" and held for
  confirmation. Beat 6 quotes that note verbatim. Do not let a future cut call it a refusal.
- No competitor accuracy claim stated as fact: 97.8% is a vendor's own marketed number
  (Digits), shown in quotes and marked unaudited; the film does not name them.
- Fixed in v6: v5's narration said "close-keeper won't fill the cell" where the run did propose a
  code and declined only to write it. Line 05 now says "It won't write it", matching the
  `NOT WRITTEN` stamp and the write-back capture.
- v6 also cuts the unspoken "classify, generate, verify, repair" line; the four pills stay and
  land silently under the counts, which is what "nobody asks" is supposed to look like.
- `storyboard: no` because the user asked to critique a watchable cut, not a plan.
