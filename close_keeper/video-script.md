# close-keeper demo video script (≤ 5 min)

Format: screen recording + voiceover. No camera needed. Recording setup: terminal
on the left (large font), the marimo console or a text editor on the right for the
architecture diagram at the end. Total target: 4:30.

## 0:00–0:35 — The problem

**Visual:** title card: "close-keeper — an agent that only pings you when there's a real decision".

**Voiceover:**
> "Every month, finance professionals lose days to the close: tying out workbooks,
> mapping transaction narratives to vendors, chasing the same exceptions they
> solved last month. Each task is small. Together they eat the week. Most AI tools
> make it worse — they guess confidently and hand you a workbook you can't trust.
> close-keeper takes the opposite bet: it does the work quietly, and only surfaces
> when there's a genuine decision to make."

## 0:35–1:05 — Who it's for, why it matters

**Voiceover:**
> "It's for anyone who runs a close — fund accountants, controllers, small finance
> teams. It matters because the close is judgment-heavy busywork: the judgment is
> scarce, the busywork isn't. close-keeper automates the busywork and protects the
> judgment. A cell it can't verify stays blank and routes to you with evidence —
> blank is an answer, not a failure."

## 1:05–2:20 — Demo, part 1: the quiet run

**Visual:** terminal. Run (pre-staged, demo/close-tieout):

```bash
research/.venv/bin/python -m close_keeper \
  "Tie out the close package (all tasks), then tell me which cells need my decision and why."
```

**Voiceover (while the agent works):**
> "One instruction. close-keeper is a Strands agent — the agent loop decides which
> of its tools to call. First it runs the tie-out pipeline over the close package:
> classify each answer range, generate values, verify, repair, and leave blank
> whatever doesn't clear the gate. Then it reads the exception queue. Watch what
> comes back: not a wall of output — a short list of the cells that actually need
> me, each with a reason and the evidence rows behind it."

**On screen:** agent calls `tie_out_workbook`, then `list_exceptions`, then replies
with the pending cells (24 across two tasks in the demo package, with evidence).

## 2:20–3:00 — Demo, part 2: the decision

**Visual:** same terminal, follow-up turn:

```
"Approve Movements Rec!F2 and F3, reject F4."
```

**Voiceover:**
> "I approve two, reject one. The agent writes only through the recorded review
> path: the decision is persisted before any workbook cell changes, approved cells
> keep the proposed value, rejected cells revert. There is no other write path —
> not because the prompt says so, because the tool enforces it."

**On screen:** `apply_review_decisions` result, then the exception queue showing
persisted statuses.

## 3:00–3:50 — Demo, part 3: memory that learns with permission

**Visual:** memory tools in the same session (or a second terminal with the
marimo console's Memory tab).

**Voiceover:**
> "When I teach it a correction, it doesn't silently become a rule. It goes through
> governance: recorded, proposed as a candidate, validated against labeled replay
> cases — positive, hard negative, scope boundary, conflict — and only then
> activated. Watch the gate refuse an activation that hasn't earned it. Next close,
> the same narrative resolves itself. That's how the exception list shrinks month
> over month without the agent ever guessing."

**On screen:** `record_correction` → `propose_rule` → `validate_rule` (eligible:
false) → `activate_rule` **refused**: "rule is not eligible for activation".

## 3:50–4:30 — Architecture

**Visual:** the mermaid diagram from `close_keeper/README.md`, rendered.

**Voiceover:**
> "Under the hood: a Strands agent loop over eleven tools. The tie-out pipeline
> does the spreadsheet work; the exception queue holds what needs a human;
> governed memory in local SQLite accumulates approved judgment. The agent loop
> runs on Strands with the model of your choice — Bedrock in deployment, any
> OpenAI-compatible endpoint in development. Everything enforcement-shaped lives
> in the tools, not the prompt."

## 4:30–4:45 — Close

**Voiceover:**
> "close-keeper: the close runs in the background, and you're only disturbed when
> your judgment is actually required. MIT-licensed, repo linked below. Thanks for
> watching."

## Recording checklist

- [ ] fresh `/tmp/close-keeper-run` (delete before recording so the run is live)
- [ ] terminal font large, notifications off
- [ ] the two pipeline tasks with exceptions take ~2–4 min — record the full run
      once, cut the wait in post (keep one tool call in real time)
- [ ] keep the refusal on screen for a beat — it's the strongest moment
