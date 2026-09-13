# Agents for Humans: building close-keeper, a financial-close agent that only pings you when there's a real decision

*Draft for builder.aws.com — bonus-points post. Publish before the submission deadline.*

---

Every month, finance professionals lose days to the close. Tie out the workbook.
Map every transaction narrative to a vendor. Chase the same exceptions they
already solved last month. Each task is minor; together they drain the week. When
I read the Agents for Humans brief — "the agent runs autonomously and only
surfaces when there's a real decision to make" — it described the design I'd
already converged on the hard way: **blank is an answer, and the human's attention
is the scarcest resource in the close.**

So I built **close-keeper**: a Strands Agents SDK agent that ties out close
workbooks in the background and surfaces only genuine decisions.

## The problem with "helpful" agents

Most AI spreadsheet tools guess confidently and hand you a workbook you can't
trust. For a close, a confident wrong number is worse than no number — it gets
filed. close-keeper takes the opposite bet: a cell it can't verify stays blank
and routes to a human with evidence. The agent's job is to shrink the list of
things that need you, never to pad the list of things it filed.

## Why Strands

I wanted the agent loop to be the thin part. Strands gave me exactly that: define
tools with docstrings, hand them to the loop, and the model plans across them. My
eleven tools wrap machinery that already existed and was already verified — a
tie-out pipeline, an exception queue with a single recorded write path, and a
governed business memory in local SQLite. The loop orchestrates; the tools
enforce.

That split is the whole architecture, and Strands makes it natural: anything
enforcement-shaped lives in a tool, not in the prompt. The prompt can say "never
write without a recorded decision," but the guarantee comes from
`apply_review_decisions` being the only tool that writes — it persists the
decision before touching a workbook, and reverts whatever wasn't approved.

## Memory that learns with permission

The piece I'm happiest with is governed memory. When a reviewer teaches the agent
"this narrative means this vendor," that correction doesn't silently become
behavior. It goes through a lifecycle the tools enforce:

1. **record** the correction (evidence, not a rule)
2. **propose** a candidate rule from it
3. **validate** against labeled replay cases — positive, hard-negative,
   scope-boundary, and conflict coverage, zero regressions allowed
4. **activate** — refused by the tool unless validation passed

Next close, the same narrative resolves itself. Month over month, the exception
list shrinks — without the agent ever guessing, and with a full audit trail of
who approved what.

## What the build actually looked like

The honest build journey: the agent loop worked on the first try (Strands plus an
OpenAI-compatible endpoint, eleven tools registered), and then reality arrived in
the tool layer — environment quirks, a pipeline subprocess that needed its own
env loader, a model gateway that was out of credits. Each fix went into the
tools, which is the point: the loop stayed thin the whole way.

The moment that sold me on the design was testing the refusals. I asked the tools
to activate a rule that had failed validation — refused. To revoke a rule that
was already revoked — refused. The agent can *ask*; it cannot *do*. For a
financial close, that's the difference between a demo and a tool you'd let near a
real workbook.

## What's next

The natural deployment is Bedrock: the agent loop is already Strands-native, so
moving the model onto AWS is a configuration change, and AgentCore would give the
run a managed home with identity and observability. The tie-out pipeline's model
is independently pluggable, so each layer picks the model that fits.

The repo is MIT-licensed and public — link in the submission. If you run a close,
I'd love to hear what your exception list looks like.

---

*close-keeper was built for the Agents for Humans hackathon (Professional Agents
track) on top of tieout, an open-source spreadsheet tie-out engine.*
