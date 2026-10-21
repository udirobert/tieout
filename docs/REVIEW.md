# Review — uncommitted work

*21 Oct 2026. Reviewed `research/uv.lock` and the untracked `quantum_settlement/`
directory. Nothing here is committed. Recommendations below; the reasoning is
in each entry.*

## Summary

| Item | What it is | Recommendation |
|---|---|---|
| `research/uv.lock` | Stale lockfile — the `agent` extra was never locked | **Commit it.** It is a real fix and it is required for `uv sync --extra agent` to be reproducible. |
| `quantum_settlement/` | A separate project: QUBO/QAOA subset-sum settlement matching for a Qollab entry | **Do not commit as-is.** Three concrete problems, all fixable, listed below. It is a sibling project, not a tieout feature. |

---

## 1. `research/uv.lock` — commit it

**What changed.** Sixteen packages added, no versions changed, no removals:
`anthropic`, `strands-agents`, `mcp`, `mcp-types`, `boto3`, `botocore`,
`s3transfer`, `jmespath`, `pyjwt`, `docstring-parser`, `wrapt`, `watchdog`,
`sse-starlette`, `opentelemetry-instrumentation`, `opentelemetry-instrumentation-threading`,
`pywin32`.

**Why it matters.** `research/pyproject.toml:15-19` declares the extra:

```toml
[project.optional-dependencies]
agent = [
    "strands-agents>=1.55",
    "anthropic>=0.40",
]
```

but the lockfile had never resolved it. `close_keeper/README.md` and the root
README both instruct `uv sync --directory research --extra agent`, so the
documented setup path was resolving fresh versions on every machine instead of
reproducing pinned ones. Now `uv lock --check` passes and the extra is pinned.

**The one removal** is a marker normalisation on `starlette`'s `anyio`
dependency (`marker = "sys_platform != 'emscripten'"`), not a version change.

**Recommendation.** Commit. It makes the documented setup reproducible, and it
is the smallest correct change in the repo.

---

## 2. `quantum_settlement/` — do not commit as-is

**What it is.** A genuinely separate project: month-end bank settlement matching
formulated as a QUBO and sampled with QAOA, built as a single-file Qollab
submission. It inherits tieout's working agreement — *quantum proposes, classical
verifies; blank is an answer* — but shares no code with it. Its only tie to this
repo is the counterparty names, which come from the anonymised fixture.

Nothing tracked references it. It has never been in a commit. It is a sibling
project, not a tieout feature, and it should probably live in its own repository.

### 2a. The committed artifacts contradict the documented claims — fix before committing

This is the important one. `PROJECT_PAGE.md` claims:

- best-of-portfolio QAOA recovers the optimal subset on **all three** solvable
  lines, each matching the golden settlement *and* the classical solver;
- mean |residual| ≈ **8,200** against ≈ **18,500** for uniformly random subsets;
- **BL-1290** is correctly routed to the exception queue.

The committed `settlement_results.json` and `exceptions.json` show none of that:

| | Claimed | Committed artifact |
|---|---|---|
| lines | 3 matched + 1 exception | **2** entries |
| targets | 10,156 / 7,220 / 10,203 | **11** and **15** |
| subsets | invoice refs (`INV-3310`) | single letters (`b`, `c`) |
| mean residual | ~8,200 vs ~18,500 | **5.3 vs 5.8**, and **7.4 vs 7.8** |
| exception queue | BL-1290 present | **`exceptions.json` is `[]`** |
| golden match | all three | first entry: **`quantum_equals_golden: false`**, `golden.subset: null` |

The artifacts are from an earlier, toy version of the scenario. The file
timestamps confirm it: `settlement_results.json` and `exceptions.json` are
timestamped 22:17, `main.py` was edited at 22:29, and the current `main.py`
emits invoice refs (`main.py:217,236`) rather than single letters.

**Two readings, and both are bad.** Either the artifacts are stale and the
claims are unbacked by anything in the repo, or the claims came from a run that
was never captured. Neither is committable as evidence.

**Recommendation.** Re-run on the current scenario and commit the *new* artifacts
alongside the claims, or drop the specific numbers from `PROJECT_PAGE.md` and
keep only what the committed artifacts show. Given the project's own rule —
"the quantum run *proposes*; exact arithmetic *disposes*" — a stale result file
undercuts exactly the claim it is meant to support.

Note that Qiskit is not installed in `research/.venv` and the project has its
own `requirements.txt` (`qiskit-optimization==0.7.0`), so this cannot be
re-run from the tieout environment as it stands.

### 2b. The videos do not belong in the tree — 12.4 MB

`demo.mp4` (3.1 MB) and `demo_v2.mp4` (9.7 MB) are screen recordings.

The repo already has a rule about this. `.gitignore:19` ignores `videos/*`
with explicit exceptions for the close-keeper film's *source* material, and
`docs/index.html` states the policy in the open: *"Hosted as a release asset, so
no video lives in the repo tree."*

**Recommendation.** Host both as release assets on the quantum repo, the way the
close-keeper film is. Keep `PROJECT_PAGE.md` and `VIDEO_SCRIPT.md` in the tree —
they are the reproducible spec, which is exactly what the repo keeps.

### 2c. `__pycache__` is ignored, but the directory should not be there at all

`.gitignore:11` covers `__pycache__/`, so it would not be staged. But it should
be deleted rather than left to be ignored — a stale `.pyc` of an old
`settlement.py` sitting next to the source is a trap, and it is one of the
things that makes 2a hard to diagnose after the fact.

**Recommendation.** Delete `quantum_settlement/__pycache__/`.

### 2d. Where it should live

Two options:

1. **Its own repository.** It is a different competition, a different
   dependency tree, and a different audience. This is the cleaner answer.
2. **Here, as a sibling directory**, if the two are meant to read as one body
   of work — which the shared working agreement suggests. If so, it needs a
   short `README.md` saying what it is, what it is not, and how it relates to
   tieout. Right now it drops into the tree with no explanation, which is the
   opposite of how every other directory in this repo behaves.

Either way it needs the three fixes above first.

---

## Also worth knowing

- `research/uv.lock` was already stale before this session — the `agent` extra
  had never been locked. It is not a side effect of anything done here.
- `skills-lock.json` is in `.gitignore` (line 44) but the file exists on disk
  and pins the marimo-pair skills. It is deliberately untracked, matching
  `.agents/`, `.claude/` and `agent/`. No action needed; noting it because
  `skills-lock.json` reads like it should be committed and is not.
