# Where close-keeper goes next — hackathon targets

**Written 20 Oct 2026, the day the FinOps entry was judged.** The film was re-cut the same
night (`videos/close-keeper-finops/`, v6) to fix the stated reason we didn't place: no existing
workflow on screen, so the refusal had no baseline. That fix is what these entries are made of.

Sources: lablab.ai, Devpost, GenAI.Works and HackerEarth listings, read on 20 Oct 2026. Rule
quotations below are copied from the event's own pages; everything else is a paraphrase and
should be re-checked against the live rules before an entry goes in.

---

## The filter that actually decides

Almost every agent hackathon requires the work to be **created inside the build window**. We
have a finished product and a two-minute film, so the interesting question is not "which event
is open?" but "which event admits prior work, or admits a prior project plus new work?"

Only two do, both read from their own rule text:

- **Open Agent Hackathon 2026** — bonus track *Wildcard [Tinkerer]: Bring Your Own Project*,
  "scored on the new work rather than prior development".
- **PayPal AI Hackathon** — *New & Existing*: an existing project is admissible if it was
  "significantly updated after the start of the Hackathon Submission Period".

Everything else below is a rebuild on someone else's infrastructure. Some of those rebuilds are
worth doing on their own merits; they are not re-submissions.

Assumptions the shortlist is filtered on, none of them verified against our own facts:
**UK-resident working professionals, 1–4 builders, online-first, no travel budget.** If any of
those is wrong — especially the country of residence — re-run the eligibility section of each
event, because "all countries excluding standard exceptions" has a list behind it.

---

## Target

| Event | Deadline (UTC unless noted) | Format | Purse | What we'd have to build | Verdict |
|---|---|---|---|---|---|
| [Open Agent Hackathon 2026](https://hackathon.genai.works/event/open-agent-hackathon-2026) | **reg closes 22 Oct 23:59** · build 22–27 Oct · submissions 27 Oct 23:45 | fully online, worldwide, 16+, teams 1–5, free | up to $20,000 (wildcard track $2,000) | a Zetaris **and** Meterless integration in five days | **Enter.** The only door the v6 film walks through as-is. |
| [PayPal AI Hackathon](https://paypalaihackathon.devpost.com/) | **12 Nov 2026** (submissions opened 1 Oct) | online, worldwide, individuals/teams/**organisations** | $69,750 advertised | PayPal as a real governed source + payout action; public repo; <3-min video; live testing access for judges | **Primary target.** Best purse, and the integration is a genuine extension rather than a logo. |
| [Vultr: Agent Rush](https://lablab.ai/ai-hackathons/vultr-hackathon) | online build **3–8 Nov**; optional on-site 8 Nov, Salt Lake City, travel not covered | hybrid, worldwide, all levels | $9,000 cash + $5,000 credits (free $200 Vultr credit) | deploy on a Vultr VM, agent actions inside their sandbox, public demo URL. "Submissions must be original and MIT-compliant" | **Maybe.** Theme fit is the best of the list; it is a fresh build, not a re-entry. |
| [Airwallex Agentic Banking](https://airwallex.hackerearth.com) | **apply by 23 Oct** · build 25 Oct – 13 Nov | online, global, teams 1–4, free | $100K in prizes and credits | agents that move money on Airwallex sandbox APIs | **Pass unless we want the build.** Biggest purse, most forced integration, and the application window is three days. |
| [Agents for Impact](https://cloud.google.com/resources/agents-for-impact-2026) | Phase I in-person Oct–Dec 2026 · **Phase III digital Jan–Mar 2027**, rolling | Google Cloud | cash prizes | a social-impact framing the product doesn't currently have | **Back pocket.** Real dates, later, and honest reframing is hard. |
| Since AI, Turku · AI for Good Lab UAE · Devpost minor events | 6–8 Nov (Finland, in person) · 8 Dec (Abu Dhabi) · e.g. Arbiter Hacks 21 Dec, $3,800 | mixed | €50,000 · — · small | — | **Skip.** Travel, theme, or prize-to-effort. |

---

## The two that matter, in detail

### Open Agent Hackathon 2026 — GenAI.Works

Registration closes **22 Oct 2026, 23:59 UTC**; the build window is 22–27 Oct; submissions close
27 Oct 23:45 UTC. Fully online, worldwide from age 16, teams of 1–5, free to enter. Employees of
the organiser and judging sponsors may participate but can't win cash.

The wildcard track, verbatim from the event page:

> **Wildcard [Tinkerer]: Bring Your Own Project** — Bring an existing project, prototype or
> concept and extend it using sponsor technology such as Meterless and Zetaris. Entries are
> judged on the same criteria as the other tracks, must integrate Zetaris and Meterless, and are
> scored on the new work rather than prior development.

Prize pool for that track is $2,000 (1st $1,000 / 2nd $600 / 3rd $400) inside an event that pays
up to $20,000 overall — Track 01 and 02 pay $3,700 each, Track 03 $3,600, plus in-kind awards
(NVIDIA DGX Spark for best use of Nemotron, Cursor credits). Scoring is out of 100. The criteria
readable from the page are **Impact 30** ("how effectively the solution addresses a meaningful
real-world problem for its intended users"), **Technical 20**, **Innovation 15**, **Demo 15**;
the remaining 20 points sit in criteria the static page wouldn't give up, so read the scoring
block in a browser before deciding what to over-polish.

The two main tracks are worth reading before choosing. **Track 02, "The Agent That Can Explain
Why":** *build agents that investigate complex questions across multiple data sources, connect
findings, and produce evidence-backed answers or recommendations.* **Track 03, "Reasoning
Architecture":** *demonstrate a novel ability to turn data, knowledge, memory, and reasoning into
reliable decisions and actions.* That is close-keeper described by strangers. The blocker is that
tracks 01–03 are governed by rule sections **04 Build window** and **05 What you can use**, whose
text is behind expand-on-click accordions and was not readable from a plain fetch — verify in the
browser whether prior work is admissible there. The wildcard states its allowance outright, which
is why it is the entry we can actually plan around.

Sponsors whose tech must appear in a wildcard entry: **Zetaris** (data access / virtualisation —
its CTO is judging) and **Meterless** — *re-read 22 Oct: it is not metering.* Meterless is an
Apache-2.0 local-first context stack for agents: **H-MEM** (a three-tier memory with provenance, an
append-only trust ledger, and preview-first "sleep" consolidation), World Model, Markovian, Scout
Intent, and an OpenAI-compatible **Meterless Runtime** at `127.0.0.1:8088/v1`. Each engine ships as
an AGENTS.md spec + TypeScript reference + conformance suite; "integrate Meterless" means implement
an engine spec in your stack and pass its conformance. Neither is in the product today. The
plausible reading of Zetaris for us is that the judgment queue stops being Seapoint-only: invoices,
the bank feed and the ledger read through one federated source, which is also the honest answer to
"does this work outside one provider's sandbox". Meterless fits the governed memory itself:
`record_correction → propose_rule → validate_rule → activate_rule` is already the H-MEM shape —
mine → store → preview-first consolidate → promote — and the tenant ledger is already a trust
ledger. Porting the H-MEM spec into `harness/memory_store.py` and passing its conformance suite is
a real integration, not a logo; Meterless Runtime is also a drop-in agent-loop provider via
`CLOSE_KEEPER_BASE_URL`.

**Day-1 status, 22 Oct:** registered. Sponsor set has since widened — NVIDIA (DGX Spark prize for
best Nemotron use), SpaceXAI with Cursor, and Bright Data joined Zetaris and Meterless. Zetaris
runs as a "local install" on `snapflip-vultr` (Ubuntu x86_64, 4 CPU, 31 GB RAM, Docker 29, 104 GB
free — meets every requirement; the Mac can't host it: 8 GB total, no Docker, amd64 emulation).
Reach it over JDBC `:10000` via SSH tunnel. Download needs a Zetaris Cloud account; hackathon
getting-started repo is github.com/zetaris/getting-started.

**Day-1 record — the five answers** (the Day-1 brief's required output):

1. **User:** the finance owner at a ~12-person company with no controller — founder or
   fractional CFO doing month-end close, working the rows the auto-matcher couldn't tie.
2. **Problem:** the unmatched queue gets resolved by *"what did we code it as last month?"*,
   and nothing records that it was a guess — the guess silently becomes next month's pattern.
3. **Goes in:** bank feed, invoices, coded ledger — read through Zetaris federation across
   sources, not one provider's API — plus the tenant's prior governed corrections.
4. **Comes out:** a short judgment queue (proposed coding + evidence rows + explicit
   refusals), audited write-back returning `change_id`, governed rules for next month.
5. **Why an agent:** matching is a script's job. Weighing conflicting evidence across live
   sources, knowing when to refuse, and carrying learned rules across months is not. A
   single prompt has no memory and no enforced write gate; a script cannot abstain.

**Build shape:** Zetaris installs on `snapflip-vultr` via its docker-compose bundle (user
downloads `zetaris-platform.zip` + registry creds from Zetaris Cloud — the one manual step).
Federate the close package: invoices/bank/GL as separate sources (file + REST cookbooks),
queue read through Lightning SQL, JDBC `:10000` over SSH tunnel. Meterless is H-MEM as a
TypeScript sidecar — the conformance runner (`npx tsx conformance/runner.ts`,
`HMEM_IMPL=<index.ts>`) requires a TS module exporting `HMEM`; reference passes 13/13 on
this machine. `harness/memory_store.py` stays the governed facade: `record_correction`→
`add(source=user_correction)`, `propose`→`dream_proposed`, `validate`→approval boundary,
`activate`→`dream_approved`+promote to long_term, `revoke`→`supersededBy` (never deleted),
tenant ledger→TrustLedgerService, `suggest`→hybrid retrieval. Meterless Runtime as model
provider is optional — its default port 8088 is already bound on the Vultr box (veles
stack; the box also runs iota/bothy workloads, so budget its resources politely). New work
goes on branch `open-agent-2026` so the wildcard's "scored on new work" diff stays legible.

**Day-1 build state:** `harness/hmem/` vendors the reference engine (`vendor/`, unmodified)
plus a tenant-scoped `src/index.ts` and an HTTP sidecar `src/server.ts` on **:8737** — one
HMEM instance per tenant, `x-tenant` on every call, `HMEM_PERSIST_ROOT` for per-tenant
persistence. `harness/hmem_client.py` is the only Python path in; `available()` is how
surfaces degrade to the SQLite store without pretending. Conformance: 13/13 against our
`src/index.ts`. Smoke-verified: add/query/ledger/feedback, tenant isolation, python client.

**Day-1 wiring state:** `MemoryStore(path, hmem=client|True)` — SQLite stays the system of
record, the engine adds recall + a second audit trail. Lifecycle mapping is live:
correction→`working` memory, propose→derived memory, activate→`promote` to `long_term`,
revoke→`superseded`, `suggest` attaches `recall` while `resolve` stays the decision. A
mismatched-tenant client is `CrossTenantWrite`; a dead sidecar degrades cleanly. The agent
surface opts in via `HMEM_SIDECAR_URL`/`CLOSE_KEEPER_HMEM` (`agent.hmem_enabled()`, probed
once, reported on stderr and in the system prompt — the agent can never overclaim recall).
68/68 tests incl. 7 engine-seam tests; live end-to-end verified (engine ledger logged
create/promote/read/update alongside the SQLite event trail).

**Day-1 surface state:** `query_close_source` (Zetaris, read-only by construction) +
`list_memory_conflicts` / `memory_sleep_preview` (engine-native ops) join the agent's
tools, each with a live/offline block in the system prompt — the agent cannot claim a
capability it does not have. Verified in a real Strands run: the model used recall and
correctly described it as corroborating evidence, not the decision. Zetaris pieces
(`harness/zetaris_client.py`, `zetaris/sql/`, `scripts/export_close_sources.py`) are
built to their tested REST contract and wait on the instance install on vultr
(`ssh -L 3300:localhost:3300`, `ZETARIS_API_KEY`). The close desk (`close_keeper/app.py`,
`marimo check` clean) now renders the story: an integrations status strip, the engine's
layered view under Memory, and the two ledgers side by side under History — "two trails
that must agree" is shown, not asserted.

**Welcome Guide deltas (read 22 Oct, authoritative):**

- Full rubric — the 20 unread points resolved: Impact 30, Technical 20, Innovation 15,
  Demo 15, **Product & UX 10**, **Sponsor Tech 10**. Ties break on Impact, then timestamp.
- **Cursor is required** — "teams must use Cursor as their development environment", and
  the sponsor-tech explanation must say how it was used. The build so far ran in Devin;
  remaining work should run in Cursor where practical, and the deck states that honestly.
- **NVIDIA "wherever it contributes"** — must appear in the sponsor-tech explanation.
  Cheapest honest fit: Nemotron via NVIDIA's OpenAI-compatible endpoint as an agent-loop
  model option (`CLOSE_KEEPER_BASE_URL`/`_MODEL` already support it); the DGX Spark prize
  is for best Nemotron use.
- **Submission needs (27 Oct 23:45 UTC):** 1–4 min demo video showing the workflow + both
  integrations; slide deck (problem/users, agent architecture, stack, sponsor use);
  public repo with README; sponsor-tech explanation covering Zetaris, Meterless, Cursor,
  NVIDIA; and **pre-existing components must be declared on the form** — the tieout
  harness and pre-branch close-keeper are exactly that. Declare them.
- Their "strong agent" vocabulary maps cleanly: verify→repair→blank loop = executor +
  evaluator; the replay gate = governance evaluator; governed store + H-MEM recall =
  shared memory; decision ledger + engine trust ledger = the reasoning trace. Frame the
  deck's architecture section in those terms.
- Security rule: no keys anywhere — `.env.example` is placeholders only, verify before
  submission (grep for sk-/Bearer/long tokens on the branch before pushing public).

### PayPal AI Hackathon

Deadline **12 Nov 2026** — the project page shows 12:00 PST and the rules page has shown 14:00
PST, so treat the earlier time as the one to hit. Submissions opened 1 Oct, so the "updated
during the period" clock started a fortnight ago and there are four working weeks left. Online;
open to individuals above the age of majority in their country, teams, and **organisations**
(which matters if this is now a company rather than a hobby); all countries and territories except
a standard exclusion list. $69,750 across overall prizes and special awards.

The prior-work rule, verbatim from [the official rules](https://paypalaihackathon.devpost.com/rules):

> **New & Existing:** Projects must be either newly created by the Entrant or, if the Entrant's
> Project existed prior to the Hackathon Submission Period, must have been significantly updated
> after the start of the Hackathon Submission Period. Entrants should explain how their Project
> was significantly updated during the Submission Period. Sponsor and Administrator will
> determine what constitutes a "significant change" at their sole discretion.

Submission also requires: meaningful use of **both PayPal and AI**, a **public open-source
repo**, all source and setup instructions, a **demo video under 3 minutes** on YouTube, and
**testing access to a working project** for the judges. Originality and ownership are warranted
by the entrant, and a project must not have been developed with financial or preferential support
**from the sponsor or Devpost** — Seapoint and 13books are not PayPal, so that clause does not
bite. Note separately that the film we already have is exactly the right length for their video
limit, but it is not an entry film until it shows PayPal.

Why the integration is not cosmetic: the close does not end with a coded journal, it ends with
money moving. Two honest uses, both of which the governance model already handles:

1. **PayPal as a source that must tie out.** Payouts and fees are transactions the bank feed has
   to be reconciled against — a new side of the match, and new rows for the judgment queue.
2. **PayPal as an action behind the gate.** A vendor payout is the highest-stakes write an agent
   can make. It goes through the same withheld-tool wrapper as `set_transaction_coding`:
   `confirm=true`, evidence attached, audit record returned. "The agent that won't write" is a
   stronger claim when the thing it refuses to do is move money.

That second point is the same argument the FinOps judges asked for, expressed against a
concrete baseline: payouts are the step a person does at 11pm today.

**Open question to settle before entering:** whether any investment has been taken in this
project. 13books Capital is on the judging side of the FinOps event, but if the relationship is
also a funding one, re-read the sponsor/investment clauses in every entry — some events exclude
already-funded projects outright.

---

## Closed, or never open to us

| Event | Why not |
|---|---|
| FinOps Hackathon (Seapoint × 13books × Claude) | Judged 20 Oct 2026. Did not place. The v6 cut is the record of the fix, not a re-entry. |
| Agents for Humans (Strands, Professional track) | Prior submission, already made. |
| [Agenthon 2026](https://www.agenthon.net/rules) | NeurIPS-track competition; registration and development closed 12 Oct, final uploads 25 Oct, **open-source models only**, scored on sealed private tests. Not built for a Claude/MCP product. |
| [Shenzhen FinTechathon 2026](https://www.its.ac.id/international/2026-10-06/2026-shenzhen-fintechathon-international-track-a-fully-funded-international-competition/) | Deadline is today, students only, grand final in Shenzhen. |
| [CDIR Agentic Regulator Hackathon](https://www.cdir.global/cdir-hackathon) | Concept notes closed in early August. Theme (AI-enabled regulation) would have fit the audit trail. |

---

## What carries into every entry

The honesty rules survived judging intact and are the differentiator, not a disclaimer, so they
travel with the project rather than being re-derived per event:

- No number spoken or written that is not measured and shown. The 0.5%, the 14 of 2,664 and the
  10 refusals are counted off the 20 Oct live pull; fixture counts never blend with live ones.
- Every capture labelled with its provenance, including "styled replay" where it is one.
- The founder is a frame, not a case study. No invented customer.
- Steps 1–2 of the close are not ours, steps 4–5 are not implemented, and no days-saved number
  exists because there is no customer. Say so before a judge finds it.
- Green means counted; orange means claim or frame. Don't let a future cut swap them.
