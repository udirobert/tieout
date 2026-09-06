# Hackathon retro — winner techniques vs. our approach (2026-09-06)

> **Active submission:** Syndicate by Maximor (Track 2) — see `SYNDICATE.md`.  
> This file is Encode retro; lessons inform Syndicate (concurrency, repair loop, factorial evals).

Post-mortem notes from the Ylookup x Encode AI Hackathon. Four techniques named by
winning teams, mapped onto what tieout actually did (evidence cited), with the
concrete change for next time. Goal: a checklist for the next research-track event.

Context: we shipped 68.00% pass_rate / 37.09% cell_accuracy on SpreadsheetBench
Verified 400 (272/400). Ship = one-shot values-first Qwen3.8-27B, thinking on via
the official `qwen3_5` renderer. Full write-up in `SUBMISSION.md`; ablation
progression table at the bottom of that file.

---

## 1. Concurrency — mostly missing; cost us experiment *throughput*, not score

**What the winners did:** run many model calls / task evaluations in parallel
(`asyncio.gather`, thread pools). Wall-clock stops scaling linearly with workload,
so you get far more experiment cycles inside a hackathon weekend.

**What we did:** all runs (tinker-400, clone-run, container400, v2b subsample) were
sequential single-flight runs. We engineered around serialism instead of fixing it
("the tinker poller cannot hang the process", overnight container runs).

**Where it hurt us:**
- Our noise band was ±2–3pp (docs/BASELINE-DELTA.md) and promotion required
  full-400 runs. LoRA v2b was killed as "within noise of LoRA-v1" — we could not
  afford seed repetition to distinguish signal from noise.
- `research/methodology-notes.md` §3 prescribes WML's repro protocol (3 seeds,
  mean±std) and §4.5 says "report mean±std where budget allows" — we never had the
  budget. Concurrency *is* that budget.

**Next time:** async fan-out over tasks is the cheapest way to buy statistical
power and extra experiment cycles. Target: 3 seeds × any config we promote, in
one overnight run, not three nights.

---

## 2. Text → Pythonic code + data cleaning — we built the best version, then shipped the values path

**What the winners did:** make the model emit structured/executable output
(Python, validated JSON) instead of free-form text, and clean inputs so errors are
mitigated before the model sees them. Executable output is deterministic to parse,
machine-checkable (run it — failure = retry/repair, not silent zero).

**What we did:** we *had* this. `docs/PATTERNS.md` code-exec loop (script →
`SUMMARY_JSON` → positive control → validator), sheet-level openpyxl codegen,
lenient parser (`harness/parsing.py`), and `write_output` coercion (dates, numeric
strings, MergedCell origin, `""==None`) — all textbook error mitigation.

But the ship (`harness/clone_run.py`) is one-shot values-first JSON: no codegen, no
repair loop, no skills. We walked away from the executable path at freeze time.

**Where it hurt us:** the parse audit
(`research/data/eval/clone_run/parse_audit_summary.json`):
- 33/400 JSONDecodeError, 25/400 truncated at the 16k cap (23 overlap)
- 35/400 fell back to init workbook → automatic fail = ~8.75pp theoretical ceiling
  left on the table (ceiling if all passed: 68% → ~74.25%)

The winners' "clean the data to mitigate errors" attacks exactly this: 35 silent
zeros from brittle JSON-after-CoT at a token cap.

**Next time:** treat parse-audit failure classes as the top roadmap item, not a
"write-up row only". Output must be structured + validated with a repair-or-retry
loop on validation failure — never init-copy-and-forget. Data cleaning upstream
(serializer quality, SheetCompressor-style structural compression per
methodology-notes §7a) reduces error sources before the call.

---

## 3. Factorial experiments — we ran a ladder (OFAT), not a grid; it mispriced our biggest lever

**What the winners did:** vary all config factors systematically across
combinations (factorial / grid), not one at a time. Catches **interactions**
(e.g., "prompt A wins at temp 0, prompt B wins at 0.7") that OFAT can never see,
and identifies the best corner with evidence instead of vibes.

**What we did:** sequential ablation ladder — hybrid → thinking-off hybrid
(54.75%) → clone-run (68.00%) → container (67.75%) → LoRA v1 → LoRA v2b. Each run
changed one thing against the previous config.

**Where it hurt us:**
- BASELINE-DELTA §1 forecast thinking-on at "+8 to +12pp"; measured +13.25pp.
  Our own note: "thinking on the official recipe is a much bigger lever than the
  prompt or parser changes we were contemplating." OFAT + a ±2–3pp noise band
  mispriced the single biggest knob until the final day.
- Never tested interactions: thinking × max_tokens (the 25 truncations at 16k are
  *exactly* a thinking × output-budget interaction) and thinking × serializer cap
  were never run ("if we ever A/B it, do it after ship" — cell never filled).
- The LoRA branch burned two full training cycles on results "within noise" — a
  cheap fractional factorial on prompt/config axes at 40–100-task subsamples would
  have located the winning corner before we spent LoRA budget.

**Next time:** small grid on a fixed subsample, then one confirmation run on the
full 400. Example grid we should have run first: thinking on/off × 16k/32k tokens
× serializer (20k cap vs full 120×30) — 8 cells × 100 tasks, concurrent, one
afternoon. Promote the winner to a full-400 run.

---

## 4. Harness tuning → cheaper reasoning tier ≈ expensive tier — we found this effect and didn't exploit it

**What the winners did:** tuned the harness (prompts, tools, retries, structure)
until a *medium* reasoning-effort model matched the high-effort model's results at
much lower latency/cost. Insight: model capability and harness quality are
substitutes; optimum = best quality-per-cost point, not the strongest model.

**What we did:** this is literally our best finding. The −13.25pp thinking-off gap
(54.75% → 68.00%, same model, same prompt, only decode path differs) *is* a
reasoning-effort result: harness/decode-path was the dominant lever, not model
capability. It's in SUBMISSION.md as "the harness gap" — but we framed it as a
finding, not a strategy.

**What we never ran:** the mirror experiment — "thinking-on costs +13pp but also
25 truncations and heavy latency; can a better serializer + structured output +
targeted repair make thinking-*off* (fast/cheap) match thinking-on?" Our own
methodology notes cite WML doing exactly this ("compiled execution sharply cut
tokens/calls while keeping wins", §3/§7c). We froze thinking-on instead.

**Next time:** treat reasoning effort as a *cost knob*. Run harness-vs-effort
grids explicitly; the frontier point is usually mid-effort + strong scaffolding.
Bonus: the latency saved feeds straight back into the concurrency budget (§1).

---

## Meta-observation

`research/methodology-notes.md` contained all four winning techniques as literature
(WML execution feedback, 3-seed protocol, skill libraries, compiled execution).
The gap: we applied the papers' *findings* but not their *experimental design* —
parallelism, factorial grids, seed replication, cost/quality frontier analysis.
Our process rule ("only run model calls to measure a published hypothesis") was
enforced on model/prompt choices but not on evaluation methodology.

## Checklist for next time

1. Async task fan-out from hour one (concurrency).
2. Parse/validate/repair loop on structured output; audit failure classes as
   roadmap, never "write-up row only" (pythonic output + cleaning).
3. Fixed-subsample factorial grid before any big run; confirmation run on the
   full set after (factorial experiments).
4. Reasoning effort as a tunable cost knob; grid it against harness quality
   (medium-tier insight).
5. Keep the holdout discipline from `docs/BASELINE-DELTA.md` — threshold
   policies, never id lists.

