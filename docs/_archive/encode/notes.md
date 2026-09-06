# Encode hackathon — notes & analysis

Merged from HACKATHON-NOTES.md and BASELINE-DELTA.md. For the full submission write-up see [submission.md](submission.md).

# Hackathon retro — winner techniques vs. our approach (2026-09-06)

> **Active submission:** Syndicate by Maximor (Track 2) — see `docs/SYNDICATE.md`.  
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


---

# task_0019 — values-first vs official 59.0% (written delta, no code)

**Status:** report only. `pipeline.py` / `adapters.py` not touched.
**Sources:** `research/baseline/tinker_predict.py` + `research/baseline/common.py`
(the published Qwen3.8-27B one-shot, values-not-formulas, 59.0% on all 400) vs
`harness/{prompts,adapters,parsing,pipeline,serializer,verifier}.py` as used for
`/tmp/tinker-400` (46.75%, no-repair values-first).
**Scoring:** both use `research/evaluate.py` + `sb.values_equal` (2dp / dates as
serials / `""==None`). Official 59% is values-not-formulas, so `--no-recalc` vs
recalc is 0pp (C confirmed: 0 formula strings in tinker-400 outputs).

Gap to close: **12.25pp** (46.75 → 59.0). Ship hybrid is 54.75% (4.25pp under
the floor) because codegen already recovered sheet-level. An official-style
values-first recovery would lift the whole ladder, holdout included.

Noise band (C): **±2–3pp** at temp 0. Treat anything under ~2pp as unproven.

---

## Official 59.0% config (the floor)

| Knob | Official (`tinker_predict.py` / `common.py`) |
|---|---|
| System | `SYSTEM_PROMPT` — identical to our `SYSTEM_VALUES` |
| User | `## Instruction` / `## Workbook` = `serialize_workbook` (120×30, no char cap) / `## Answer range` (sheet + `answer_position`) |
| FORMAT_HINT | Appended in the completer: JSON only, example `B6=42`, `B7=null`. No multi-sheet example. |
| Thinking | Cookbook `qwen3_5` renderer (thinking **on**). `renderer.parse_response` keeps text parts, drops think. |
| Template / stop | `renderer.build_generation_prompt` + `stop=renderer.get_stop_sequences()` |
| max_tokens | **8192** (flag default) |
| temp / n | 0 / 1 |
| Repair | None. One call. Init workbook on any exception. |
| Parse | Strip `<think>…</think>`, first `{` to last `}`, `json.loads` → pydantic. No number coerce. |
| Write | `cells[coord.upper()] = raw value`. No sheet-qualified keys, no date coerce, no MergedCell handler. |
| Skills / pin / 20k | None |

`llm_predict.py` is the same prompt/schema via OpenRouter structured output — the
59.0% Qwen number is the Tinker one-shot, not a different prompt family.

---

## Ranked deltas (ours minus official)

### 1. Thinking off — **+8 to +12pp** (high expected, medium-high confidence)

**Official:** `qwen3_5` renderer, thinking on, think stripped at parse.
**Ours:** `apply_chat_template(..., enable_thinking=False)` then raw
`tokenizer.decode`. Same empty-think prompt as `qwen3_5_disable_thinking`
(`research/methodology-notes.md` §6b).

This is the only knob large enough to explain most of 12.25pp. C's
RESULTS_CHECKLIST §C said the same. We turned thinking off because CoT leaked
as plain text and drowned JSON; official already solved that with
`renderer.parse_response` (keep `type==text` parts only).

**Do not** flip `enable_thinking=True` on the current HF-template path — that
re-opens the leak. The official-matching change is: `get_renderer` +
`build_generation_prompt` + `parse_response` + renderer stop sequences.
Generic. Holdout-safe.

**Risk:** latency and tokens go up (think is test-time compute). JSON parse
failures if parse_response is wired wrong. Measure on a 40-task slice before
a 400.

### 2. 20k workbook cap — **+1 to +2pp** (medium)

**Official:** full `serialize_workbook` 120×30, no further cut.
**Ours:** `MAX_WORKBOOK_CHARS = 20000`, then a pinned answer-range excerpt.

A dense 120×30 preview is often >20k chars. Official sees the grid; we see a
truncated prefix + pin. C's 29 "missing/truncated range" fails are a mix of
true >120-row sheets (official also blind) and 20k-only cuts. Removing or
raising the cap to “whatever 120×30 is” is the official-aligned move.

Pin itself is extra vs official (see §5). Cap removal and pin are separable.

### 3. Stop sequences missing — **+0 to +0.5pp** (low)

**Official:** `stop=renderer.get_stop_sequences()`.
**Ours:** none. Lenient parser usually saves us. Cheap to add once we are on
the cookbook renderer. Not a 12pp story.

### 4. FORMAT_HINT drift — **~0pp** (low)

**Official:** `B6` / `B7` same-sheet null example.
**Ours:** `B6` / `Sheet2!A1` plus “Use Sheet!A1 when the answer spans more
than one sheet.”

System prompt is byte-identical. Hint change is small. Aligning to official
is cheap if we do an official-clone run; not worth a solo experiment.

### 5. Prompt extras official does not have — **0 to −1pp combined** (low)

We add, official does not:

- Pin excerpt (addresses+values on the values path). Can help after
  truncation or cause echo (hybrid-v2: omit cost 8/27; scoped pin did not
  beat the old 48% cell rate).
- `data_position` line when present.
- Category **skill fragments on the values user prompt**
  (`build_values_prompt` → `_skill_fragment`). Official values-first has
  none. Skills were meant for codegen system. On values they are extra
  tokens, holdout-generic, but not part of the 59% recipe.

None of these explain 12pp. For an official-clone measurement, drop them
for that run only.

### 6. max_tokens 16384 vs 8192 — **0pp vs official** (high)

We have *more* output headroom than official. This cannot be why we are
below 59%. Do not cut to 8192 to “match” — Qwen docs prefer 16k, and
large JSON answers truncate at 8k.

### 7. Parse / write (we are already ahead or even) — **0 to +1pp already on our side**

| | Official | Ours |
|---|---|---|
| JSON | first `{`…last `}` | raw_decode + list wrap + bare `{cell,value}` |
| Numbers | written as the model emitted | numeric strings → int/float; leading-zero tokens stay text |
| Dates | raw ISO string | coerce to datetime when number format looks like a date |
| Keys | `coord.upper()` only | sheet-qualified `Sheet!A1` + unique bare coord |
| MergedCell | `ws[coord]=` can throw | write through merge origin |
| null | None | `""` (scorer treats `""==None`) |

These recover tasks official can drop. They do **not** close a 12pp deficit.
Do not revert them to “match official.”

### 8. Repair (≤3) — **not in the 12.25pp gap**

`/tmp/tinker-400` was no-repair, like official. Current pipeline repair is a
*later* layer. values-pin (repair on) went 48% → 43.64% cell — within/near
noise plus distribution shift, not a reason to add repair to an official
clone. First measure one-shot official-style; then decide.

### 9. Scoring params — **0pp**

Same scorer, same `values_equal`, same `--all`. Recalc is a no-op on
values-only workbooks. Not a config miss.

### 10. `#N/A` treated as a formula error — **−0.5 to −1pp if several lookup golds are `#N/A`** (low)

`verifier._XL_ERR` includes `N/A`. Sanity + soffice postcheck reject a
literal `#N/A` and trigger repair/fallback. Official writes the string and
the scorer can match it.

SUBMISSION.md now describes a **general** rule: `#N/A` is a valid
missing-lookup scalar (e.g. outer lookups that legitimately yield
unresolved references for missing source entities), not a fatal Excel
error. `#REF!` / `#NAME?` / `#VALUE!` / `#DIV/0!` stay fatal. The earlier
id-keyed "whitelist" (165-23, 47933, 55427) was a discovery artifact, not
ship behavior, and was removed in `task_0022` (de-id-keying); the ship
verifier does not branch on task id.

---

## What this is not

- Not a model-size gap. Same `Qwen/Qwen3.8-27B`.
- Not scoring / recalc.
- Not max_tokens (we are already above official).
- Not “add more pin/overlay variants” (frozen; sub-noise).
- Not per-id patches for 13-1 or the 27 dip set.

---

## Holdout discipline

Judges run the container on a set we have never seen. Id-keyed behavior
scores 0 there.

**In `harness/*.py` today:** no `if task["id"] == …` branches. Classify is
`instruction_type` contains `"sheet"`. Skills are keyword-on-instruction.
Pin-scope is path-based (codegen vs values). Resume skip is
predictions.jsonl, not a baked id list.

**Id-keyed artifacts that must stay out of the ship path:**

- `research/data/cell_dip_ids.txt` — analysis only.
- ~~SUBMISSION `#N/A` task ids~~ — done in `task_0022`; SUBMISSION.md now
  carries a general missing-lookup policy, no per-id whitelist.
- B sampler skip files — data-gen, not the container.

**Do not add:** new id lists, per-id prompt overrides, known-too-large skip
lists in the harness. A “too large” policy if we ever need one is a
*threshold* (cell count / serialized chars), not an id file.

---

## Recommended next cycle (closed by clone-run, task_0024)

The recommendation was one measurement, official-shaped, then stop if it
is inside noise.

1. **Clone-run (values, one-shot, thinking via `qwen3_5` renderer +
   `parse_response` + renderer stops).** Official SYSTEM + FORMAT_HINT +
   uncapped 120×30 serialize. Keep our parser/write (strictly more
   permissive). `max_tokens=16384`. No skills, no pin, no repair.
   Temp 0. Full 400.
2. Score `--all --no-recalc`. Compare to 46.75 / 54.75 / 59.0.
3. **Result: 68.00% (272/400).** Way above the 59% official floor. Promoted
   to ship. Old hybrid 54.75% superseded (harness-gap: thinking off, wrong
   decode path).

Forecast (from §1 expectation, "thinking on" hypothesis): values-first in
the 56–61% band, hybrid stitch around 60–63%. **Measured: 68.00% plain
values-first** — thinking on the official recipe is a much bigger lever
than the prompt or parser changes we were contemplating. The lift is
purely decode-path, holding the model and the official prompt constant.

---

## Post-clone-run (measured) — max_tokens vs 25 truncations

**Ship config is frozen** at clone-run: `max_tokens=16384`. Do not change it
for the container-400.

`/tmp/clone-run-400/parse_audit_summary.json`: **25/400 truncated** at 16k
(`output_tokens >= 16384`). **23/25** of those are also `JSONDecodeError`
(`both=23`). Two truncated replies still parsed.

Ceiling if every truncated task became a golden pass: **+25/400 = +6.25pp**
(68% → 74.25%). That is not a forecast.

Realistic band: **+1 to +3pp**, low–medium confidence.

- 23 tasks never emitted parseable JSON because think filled the 16k budget.
  More tokens can let `parse_response` reach a closing `}` — or the model
  just thinks longer. We already doubled official's 8192 and still hit the
  cap on 6.25% of tasks; 32k is not guaranteed to close them.
- Even with valid JSON, many of those 23 are large sheet ranges (the ones
  that burned 16k). Golden pass is not automatic.
- The 2 truncated-but-parsed tasks are already in the 272. Raising the cap
  does not help them.
- Overnight container cost/latency scales with the cap. 16k is already the
  Qwen-recommended headroom.

Not a promotion lever. Write-up row only. If we ever A/B it, do it after
ship on a 25-id slice, not a config change in the frozen image.
