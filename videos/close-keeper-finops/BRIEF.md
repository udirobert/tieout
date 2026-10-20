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

The submitted two-minute demo film for the FinOps Hackathon (20 Oct 2026). Four beats:
someone has the problem alone at midnight → the books are read live, and the quiet work is
what matters → it has to *earn* an answer before anything is written → the stakes, why the
unwritten cell is the difference between an agent a fund can adopt and one it can't. Tone:
quiet, precise, editorial. No talking head, no music swell, no narration over the refusal.
Motion doctrine inherited from `videos/tieout-demo`: land, don't fade.

Delivered as `renders/close-keeper-finops_*.mp4` (ignored; re-render with `npm run render`
after regenerating audio).

## Assets

- `assets/footage/close-keeper-live-seapoint.mp4` — 13.4s, beat 2. Styled replay of the real
  20 Oct Seapoint MCP pull: spend by category, the 0.5% thesis, the judgment queue.
- `assets/footage/close-keeper-governed-refusal.mp4` — 17.0s, beat 4. Real local run, key-free,
  no model: two refusals, then an activation earned on 7 labeled replays.
- `assets/img/cap-queue.png` — crop of the live session's own `Why I won't code it` table
  ("Would refuse / route to you (10)"), beat 3. The 78MB source `.mov` lives on the Desktop,
  not in git; this crop is the durable copy.
- `assets/img/cap-writeback.png` — crop of the real ledger write-back gate for the Connolly
  transaction, beat 4.
- `assets/img/*.png` (ignored, regenerable) — risograph character cutouts via the ElevenLabs
  Images API, `model_id: gemini-3-pro-image`. Text-free by instruction, so nothing in the
  character layer reads as evidence.
- `assets/voice/00–05.mp3` (ignored, regenerable) — `scripts/build_audio.py`, ElevenLabs
  George / `eleven_multilingual_v2`. Measured durations drive every scene boundary; scene
  starts are 0 / 11 / 30.5 / 55 / 79 / 100.5.
- `close_keeper/video-script.md` — the story spine and recording plan.

## Customizations

- Count-up on the 14 in beat 3; three-second hold on the contradiction in beat 5 with no new
  text and no narration.
- Rubber-stamp land on the refusal (`scale 3.5 → 1`, `power4.in`) plus a frame shake.
- Sentence-chunk captions timed to the measured VO, never two in the same band at once.
- BGM was attempted and abandoned — the ElevenLabs music endpoint 404'd, and the film works
  on narration alone. The silent holds are intentional, not unfinished.

## Notes

- Honesty rules that survived to the final cut: no invented customer (the founder is a frame,
  not a case study); no number spoken that is not on screen; every capture labelled with its
  provenance, including the Seapoint clip's "styled replay of the live pull".
- The live session disproved one earlier rule. close-keeper **does** write to Seapoint — via
  `set_transaction_coding`, held behind an explicit go-ahead, returning `change_id` audit
  records. The film says "nothing writes until you say so" rather than "it never writes".
- Two counts that must not be conflated: **14** is `needs_review 7 + unreconciled 7` from the
  distribution; **10** is what the agent said it would refuse to code. Beat 3 shows both,
  labelled, so the difference is on screen rather than a discrepancy a judge has to catch.
- Meridian Insurance was coded with a warning in the real run, not refused outright — the
  agent flagged "also recategorises from Legal & Professional Fees → Insurance" and held for
  confirmation. Beat 5 quotes that note verbatim. Do not let a future cut call it a refusal.
- No competitor accuracy claim stated as fact: 97.8% is a vendor's own marketed number
  (Digits), shown in quotes and marked unaudited; the film does not name them.
- Known soft spot: narration line 04 says "won't fill the cell" where the run did propose a
  code and declined only to write it. Re-record that line as "it won't write it" if the film
  is ever cut again.
- `storyboard: no` because the user asked to critique a watchable cut, not a plan.
