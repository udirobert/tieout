# close-keeper — 2:00 demo video script (FinOps Hackathon, 20 Oct 2026)

> **Superseded as a shoot plan.** The delivered film is `videos/close-keeper-finops/`
> (`index.html` for what is on screen, `audio_request.json` for the words actually
> spoken, `BRIEF.md` for provenance). This file is kept for the live-slot contingency
> and the landmines list at the end — read those before the 21:25 slot, and treat
> `audio_request.json` as the source of truth for every number.

Hard limit: **two minutes**. Code freeze **20:20**. Start recording **20:05**.
Narration is ~292 words ≈ 1:57 at 2.5 words/sec, plus a 3-second silence.

## The story, before the features

Four beats, in this order, and don't rearrange them:

1. **Someone has a problem.** A founder, 11pm, proving their own numbers with nobody to help.
2. **The offer.** The agent does the work — quietly, alone, unattended.
3. **The turn.** It *stops*. Refuses the human who taught it. This is where the film is about
   something other than speed.
4. **The stakes.** Why a fund can let this near a ledger when it can't let the others near it.

Everything before beat 3 exists to make beat 3 land. The tie-out is the setup; the refusal is
the point. If you only get one thing right, get the silence after "Refused" right.

**One rule about the founder:** one sentence, then never come back to it. It is a framing of
who this is for, not a case study. Never say "we watched a company" or "our user" — there is no
customer, and inventing one on a stage judging *safety and oversight* would destroy the exact
thesis the video is making.

Format: screen recording + voiceover. No camera, no talking head, no music swell. A video about
an agent that doesn't interrupt should not interrupt you either.

---

## Shoot plan

**Already staged, free, no credits (19:55):**

- `/tmp/close-keeper-video/queue/exceptions.json` — 15 exceptions with evidence rows, key-free
  (`./demo/simulate_demo.sh close-tieout-bank-cp /tmp/close-keeper-video/queue init`).
- `/tmp/close-keeper-video/refusal_take.py` — **beat 3's turn, end to end**, three refusals and
  one earned activation, no model, no key. Verified output quoted below.
- `/tmp/close-keeper-video/memory/` — two-cycle synthetic scenario, generated.
- `/tmp/close-keeper-video/cards.html` — cold card, wedge card, the-number card, the-0.5% card,
  end card, and four caption lower-thirds. Screenshot at 1920×1080.

**Remaining, in order:**

1. **Seapoint OAuth in Claude Code** — the only missing beat.
   `! claude mcp add --transport http seapoint-staging https://mcp.seapoint.dev/mcp` → `/mcp` →
   authenticate. Record that one exchange; ten seconds of it is enough.
2. **The long tie-out run** (spends W&B/Tinker credits — your call, allow 2–4 min):
   `research/.venv/bin/python -m close_keeper --no-seapoint "Tie out the close package (all tasks), then tell me which cells need my decision and why."`
   Fresh `/tmp/close-keeper-run`. This is the only source for the tool-trace claim in beat 2.
   For a clean frame, prefix `env -u NEO4J_URI -u NEO4J_USER -u NEO4J_PASSWORD` (the dead Aura
   host otherwise prints a resolver error), or keep it and say one clause about degrading cleanly.
3. **20:05 — voiceover**, one take per beat.
4. **20:15 — export, upload, submit.** Submitting takes longer than you think.

Do not try to make the standalone agent call live Seapoint tonight — `.env` has no
`SEAPOINT_MCP_TOKEN` or client credentials. Claude Code handles OAuth itself. One live beat in
Claude Code plus local agent beats is honest, faster, and reads the same on screen.

---

## 0:00–0:14 — Someone has a problem

**Visual:** full-bleed exception list, no title card. `/tmp/close-keeper-video/queue` printed by
`harness/exceptions.py review`. **Caption: `simulated run — construction, not model evidence`.**

> "Every month, a founder opens a spreadsheet at eleven o'clock and tries to prove their own
> numbers. No controller. No finance team. This is the close when nobody is left to do it."

## 0:14–0:32 — The proof of plumbing

**Visual:** Claude Code, real OAuth'd session, typing the sponsor's own first prompt.

```
What did we spend last month, broken down by category?
```

**Caption:** `live — Seapoint MCP · read with your permissions`

> "So we handed it the books. Seapoint MCP, live — accounts, transactions, invoices, read with
> my own permissions. Ask what we spent last month by category, and burn, cash and runway come
> back in seconds. But asking isn't the point. Watch what happens when nobody asks."

## 0:32–1:02 — It works alone

**Visual:** tool trace — `tie_out_workbook`, then `list_exceptions`. Time-lapse the wait; keep
**one** tool call in real time so it reads as actually running.
**Caption:** `local close package — no live account touched`

> "One instruction, then it works alone. Classify every answer cell, generate the value, verify,
> repair up to three times. And this is the part the others don't have: anything that doesn't
> clear the gate stays blank. Of 2,664 transactions, 2,629 reconcile themselves and **14 need a
> human — 0.5%**. None of them guesses. What the human gets isn't a wall of output — fourteen
> lines, each with a reason and its evidence."

**Say the number that is on your screen.** The shipped film says **14 of 2,664 = 0.5%**, read from
the live 20 Oct Seapoint pull. Two other counts exist and must not be mixed into it: the local
`demo/close-tieout` fixture surfaced **24** exceptions, and the key-free simulated queue holds
**15**. Live vs fixture, every time, out loud.

**If the agent run doesn't happen:** cut "One instruction, then it works alone" and the
eleven-tools idea entirely. Without a visible tool trace that is an autonomy claim, *Agent
autonomy* is one of six criteria, and a judge checking it costs you the whole film.

## 1:02–1:18 — One way in

**Visual:** follow-up turn, then `apply_review_decisions` and the queue statuses changing.

```
Approve Movements Rec!F2 and F3, reject F4.
```

> "Then the human decides. Two approved, one rejected. The decision lands in the review record
> before any cell changes — approved keep, rejected revert. One way in, and the ledger door
> only opens on a confirmed, evidenced call that hands back its own `change_id`."

*(Shipped wording for this beat is `audio_request.json` line 03 — the Connolly Accountants
confirm, "Nothing on the ledger moves without me." The old clause "there is no door on the
ledger side" is false since `ef13c67` and must not be said.)*

## 1:18–1:49 — The turn ← the whole reason this entry exists

**Visual:** `research/.venv/bin/python /tmp/close-keeper-video/refusal_take.py`. No model, no
key. Verified output:

```
[close-keeper] record_correction(narrative="EXAMPLE SERVICES", vendor="Example Services Ltd")
             correction : c141e8da — evidence; it influences nothing yet
[close-keeper] propose_rule(c141e8da)
             rule       : c2564271  'example services' -> 'Example Services Ltd'
             status     : candidate — still inert
[close-keeper] activate_rule(c2564271, reviewer='quincy')   << before validating
             REFUSED: rule has no validation: c2564271-1437-488a-8377-b97d524e939b

[close-keeper] validate_rule(f1f46a7b, cases=1 positive-only replays)
             eligible     : False
             coverage     : positive=True, hard_negative=False, scope_boundary=False, conflict=False
[close-keeper] activate_rule(f1f46a7b, reviewer='quincy')   << coverage failed
             REFUSED: rule is not eligible for activation: f1f46a7b-fcef-4701-bd08-3fcb8f9e5181

[close-keeper] validate_rule(f1f46a7b, cases=7 labeled replays)
             eligible     : True
             coverage     : positive=True, hard_negative=True, scope_boundary=True, conflict=True
[close-keeper] activate_rule(f1f46a7b, reviewer='quincy')   << same call, now earned
             status     : active
[close-keeper] suggest_mappings(next month, same narrative)
             decision   : suggested   vendor: Example Services Ltd   reason: approved exact alias
```

**Caption:** `governed memory · direct tool call · no model` — honest, and a judge who pauses
finds the same claim in the repo. The value of this take is that the *camera never leaves one
screen*: refusal, then earned activation, then it resolving itself next month, in a single scroll.

> "And here's the part I'd show a partner. I teach it a correction — this narrative is Example
> Services. It offers a rule, then has to earn it: replayed against labeled history, zero
> regressions, or nothing. Look at the coverage line. hard_negative false. Refused. To my face,
> by the tool."

**Hold `REFUSED: rule is not eligible for activation`. Three seconds. Say nothing.**
Let the audience feel that they are waiting for something that isn't coming.

> "Everyone in AI accounting sells you accuracy. 97.8%, taken on faith. We sell the 0.5%
> it won't take on faith. That's an audit trail, not a benchmark."

## 1:49–2:00 — The stakes

**Visual:** the-number card, then the end card from `cards.html`. No architecture narration — a
judge reads the repo, and an explained diagram is 25 wasted seconds.

> "Enterprise close software needs a controller and a hundred and fifty thousand a year. A
> twelve-person startup has neither — and deserves better than a guess with a decimal point on
> it. close-keeper."

**End card only, no narration, 2 seconds of hold before you cut:** `repo · github.com/udirobert/tieout`
`no-key demo · molab · close_keeper/demo_app.py`

---

## Landmines — do not say these on camera

The room is Seapoint (sponsor, €7.5M seed in April led by 13books Capital) and 13books Capital
(the investor). Both know this market cold, and one of six criteria is *Safety and oversight*,
so an overclaim costs more than the claim buys.

- **"It writes nothing to the ledger."** It does now — we demonstrated it on stage today, so
  saying otherwise in the room is checkable in one question. The true claim is stronger: the raw
  Seapoint mutating tools (`set_transaction_coding`, `set_transaction_vendor`,
  `approve_reconciliation`, …) are **never handed to the model**; `seapoint_writes.py` exposes
  wrappers that refuse without `confirm=true`, refuse a confirmed write with no `evidence`, and
  return Seapoint's own `previous_*` value and `change_id`. Say: *it can write, but only through
  a confirmed, evidenced, logged step — the capability to write silently has been withheld.*
- **"Autonomous writes" / "it fixes the books by itself."** The reverse of the above, and the
  claim the whole film argues against. The autonomy is in the reading and the flagging.
- **"We automate reconciliation."** Seapoint's homepage already shows invoices matched to bank
  transactions and synced to Xero. Position above it, never against it: *Seapoint resolves the
  clean majority; this is the judgment queue that's left.*
- **Enterprise-close vocabulary** — "account substantiation," "autonomous office of the CFO,"
  "SOX readiness." Their ICP is pre-seed to Series A, UK/Ireland. Use **burn, cash, runway**.
- **A customer you don't have.** The founder in the opening is a frame, not a case study.
- **Borrowed statistics.** Skip "88% of spreadsheets contain errors" and "$3T to the US economy"
  — meme provenance, and this audience checks. Clean numbers if you need one: APQC's August 2026
  survey of 10,198 orgs puts median close cycle time at 6.0 days; CPA exam candidates fell ~43%
  from 2016 to 2024.
- **"Autonomous"** as its own selling point. Digits calls itself the Autonomous General Ledger at
  a claimed 97.8%. Your argument is that unreviewed autonomy near a ledger *is* the problem.

## If running long

Cut in this order: "and there is no door on the ledger side" (−4s) → the "burn, cash and runway"
clause (−6s) → the spoken BlackLine line, let the card carry it (−10s). Never cut the silence,
and never cut "None of them guesses."

## Recording checklist

- [ ] fresh `/tmp/close-keeper-run` and a fresh take5 db — both deleted before recording
- [ ] terminal font large; notifications off; **no secrets in frame** (`.env`, tokens, keychains)
- [ ] `git status` reviewed for anything you didn't mean to show
- [ ] live vs fixture caption on every beat — it reads as rigour, because it is
- [ ] the number spoken matches the number on screen (**14 of 2,664 = 0.5%** live; 24 is the
      local fixture, 15 is the key-free simulated queue — never blend them)
- [ ] 2:00 file length, exported and uploading by 20:15

## 21:25 live slot (top five) — contingency

Rehearse the same 120 seconds standing, no typing, same four beats. Lead the live version with
the refusal, not the tie-out: if the network dies you still have the best 30 seconds of the
entry. Fallback order: (1) the Claude Code capture, (2) `close_keeper/demo_app.py` molab static
preview session (`73982b7`) — no keys, no network, (3) the exception-list screenshot.

If a judge asks the one question this story invites — *"isn't leaving it blank just the agent
giving up?"* — the answer is the fourth beat: it blanks, and it asks once, and the next month it
doesn't have to, because a human approved the reasoning. Blank is not the end of the workflow.
It is where the workflow becomes auditable.
