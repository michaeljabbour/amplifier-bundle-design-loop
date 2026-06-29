# Design Harness — Architecture & Build Spec

Target state for `amplifier-bundle-design-loop`: a governed, self-improving design
harness. This document is the contract; the code implements it.

Diagrams: `docs/design-loop-harness.png` (the governed loop), `docs/design-loop-metaharness.png` (the two clocks).

---

## 0. The three tiers (and the one test that separates them)

| Tier | What it is | Value / cost |
|------|-----------|--------------|
| **A — linear recipe** | one pass, no memory | value = quality of one pass; fixed cost |
| **B — looping automation** | governed loop converges one artifact to a bar | value = quality-to-bar per task; still ~fixed cost (amnesiac at the task boundary) |
| **C — compounding** | run N+1 is better/cheaper *because* run N happened | value rises and cost falls at the **task class**, not the instance |

**The C test:** *does the next task inherit anything?* Today the ledger is named "the
memory" but is per-pass/intra-run and nothing reads it across runs — so we are pre-B.
C requires (1) a **cross-run** capital account, and (2) at least one **ratchet**: a
recurring Judge catch that has become a deterministic lint with a passing regression
test, firing free on the next run.

---

## 1. Component contract (the governed loop — tier B)

The whole design rests on one structural bet: **no single LLM both scores and makes.**

| Module | Responsibility | KEY property |
|--------|----------------|--------------|
| **Controller** | drives the state machine; budget, stopping rules, best-so-far, rollback | **deterministic — never an LLM** (a `tool-*`, not a prompt) |
| **Observer/Renderer** | render maker HTML in a sandboxed iframe; stable screenshot | deterministic; **real artifacts only** |
| **Lints** | un-gameable ground-truth checks; run **before** the judge | objective; **build FIRST**; hard gate + anchor |
| **Critic (Judge)** | score 8 qualities from the *render* against a FROZEN rubric | blind to maker intent; sees screenshot + lint facts only |
| **Planner** | read ledger → highest-leverage / lowest-regression fix-batch; skip dead fixes | the anti-collusion firewall; makes nothing, scores nothing |
| **Maker (Proposer)** | apply a fix-batch → real HTML | **blind to the rubric**; optimises directives, never the score |
| **Ledger** | append-only record of every candidate, score, lint, decision | single source of truth; the capital account |

Firewall chain: **Critic → (scores) → Ledger → Planner → (directives) → Maker.**
The maker never touches a number; the critic never touches the maker's reasoning.
Collusion has no channel.

The 8 qualities (each 0–4): clarity, elegance, restraint, empowerment, agency, ease,
character, point.

---

## 2. Controller state machine

`working_head` = candidate the maker edits next. `best` = best-so-far. Rollback = `working_head ← best`.

```
INIT   load APS (bar, budget, floors[], ε, k, width=1); working_head ← brief
PLAN   Planner selects fix_batch from (ledger, latest scores, lints)
MAKE   Maker emits HTML from working_head + fix_batch
OBSERVE render → screenshot + lints
        └ lint HARD-FAIL → record INVALID_LINT_FAIL → ROLLBACK (no judge spent)
JUDGE  Critic scores 8 dims (blind)
EVALUATE  deterministic MACA accept/reject (see §3); append ledger; on ACCEPT swap best
GATE   1. best.total ≥ bar AND ∀dim ≥ floor          → DONE
       2. budget exhausted                            → DONE (return best)
       3. ∃dim in best < floor                        → ESCALATE
       4. plateau: Δbest < ε for k passes             → ESCALATE
       5. REJECTED_REGRESSION                         → ROLLBACK; mark strategy dead;
                                                         retried already? ESCALATE : PLAN
       6. otherwise                                   → PLAN
ESCALATE human resolves (raise/lower bar | +budget | pick Pareto winner | accept best)
DONE   always return the best artifact ever seen
```

All four stopping rules live here, all deterministic. The controller reads ledger
numbers against APS thresholds; it never calls an LLM.

---

## 3. MACA accept/reject — suppression-aware (min, not mean)

Objective is **lexicographic, never the sum**: `key(C) = (worst_dim(C), total(C))`.

```
reject INVALID      if lint hard-gate fails
reject REGRESSION   if ∃dim: dim_C < dim_best − τ      (τ=0 on no-regress dims)
accept NEW_BEST     if worst_dim_C > worst_dim_best
                    OR (worst_dim_C == worst_dim_best AND total_C > total_best)
reject NO_GAIN      otherwise
```

`worst_dim(best)` is monotonic non-decreasing → **monotonic improvement guaranteed**.
The regression veto (not the controller's mood) forbids trading B away to buy A.
Gaming flag: a subjective dim rises while its lint anchor contradicts (e.g. clarity↑
but text:chrome↓ and dom_nodes↑) → `suspected_gaming`, distrust the gain, escalate.

---

## 4. Judge / Maker / Planner firewall

| | Critic (Judge) | Maker (Proposer) | Planner (firewall) |
|---|---|---|---|
| **SEES** | screenshot; lint facts; frozen rubric + exemplars | current HTML; planner directives; lint facts | everything: ledger, scores, lints, fix history |
| **NEVER SEES** | HTML source; maker rationale; planner directives; **prior scores** | **rubric weights**; numeric scores; dim-defs-as-targets | — (but makes no HTML, no scores) |
| **EMITS** | 8 integer scores + per-dim **reason + signature** | real HTML only | a fix-batch (qualitative directives) |

Enforced in Amplifier by spawning judge/maker/planner as **separate agent-bundles**
via `tool-task` with `context_depth="none"` and tool least-privilege
(`exclude_tools`): the judge has no write tool, the maker never receives the rubric.

---

## 5. Ledger — the cross-run capital account

One record per **pass attempt** (including attempts that never reach the Judge).
Append-only; cross-run; keyed by `task_class` + `signature`.

```json
{
  "run_id": "r-2f9c…", "task_class": "landing_page", "pass": 3,
  "ts": "…", "rubric_version": "<judge-bundle git SHA>",
  "parent_ref": "sha256:…", "artifact_ref": "sha256:…",
  "signature": "low-contrast-cta:landing",
  "fix_batch": [{"fix_id":"…","target_dims":["clarity"],"directive":"…","strategy_tag":"…"}],
  "lint_results": {"renders_ok":true,"network_request":false,"wcag_contrast_min":4.7,
                   "focus_reachable":false,"dom_nodes":820,"text_to_chrome_ratio":0.34,
                   "viewport_overflow":false},
  "outcome": "regression_reject",   // accepted | lint_reject | judge_below_bar | regression_reject
  "scores": null,                   // 8-vector, or null if no judge call was spent
  "min_quality": null, "delta": null,
  "reject_reason": "focus_reachable<floor",   // required whenever outcome != accepted
  "judge_call_id": null,
  "cost": {"judge_tokens": 0, "wall_ms": 480}
}
```

**Writers (co-authored, in pass order):** Lints append `lint_results` (and seal as
`lint_reject` on hard-fail, stopping the pass); Judge appends `scores`/`min_quality`/
`judge_call_id`; Controller appends `outcome`/`delta` and updates best-so-far.

**Invariants:** append-only (best-so-far is a query, never mutated); rejects carry
reasons (this is what makes "skip dead fixes" real); scores are `null` on lint-reject
(never fabricate a zero); every record stamps `rubric_version` (= judge bundle SHA);
`cost.judge_tokens` is recorded (the falling-cost C-signal, harvested from the
canonical event stream).

---

## 6. Asset 8 — the promotion gate (the ratchet → tier C)

Every recurring thing the expensive Judge catches should graduate **leftward**:

> subjective judgment → versioned rubric criterion → few-shot exemplar → deterministic lint

**In Amplifier the slow clock is a git/PR/CI loop.** A promotion is a **pull request**
to this bundle: add a predicate to `tool-design-lints` + bump the rubric in the
`design-judge` bundle (drop that criterion) + add a known-bad/known-good fixture pair
to `tests/`. **Human ratification = merge.** Land on `main` + bundle-cache refresh →
the next run inherits the check for free. A `harness-evolution` recipe mines the
ledger, drafts the PR, opens it; the human merges.

**Candidate detection:** mine the ledger across runs for a `signature` where the Judge
repeatedly penalises the same quality for the same, *measurable* reason.

**The gate — all five must hold (min-not-mean, recursed):**
1. Recurrence across **≥ N distinct runs** (not passes of one run).
2. Determinism — expressible as a measurable predicate; else it promotes only to an exemplar, stays a judgment.
3. **Precision on the exemplar bank** — the candidate predicate fires on **none** of the bar-clearing artifacts (a single false positive blocks it).
4. **Human ratification** (the green arrow = PR merge) — every promotion permanently alters what the harness accepts.
5. **Bundled regression test** — ships with a known-bad (it must catch) + known-good (it must pass) fixture pair into the bundle's CI, or it does not ship.

**Demotion is symmetric:** a promoted lint that false-posits in production walks back
to a Judge criterion (a revert PR) — same evidence, same ratification. A ratchet that
can only tighten eventually seizes.

---

## 7. Governance — two human altitudes

- **Fast taste-fork** (per artifact): cheap, frequent early, should get **rarer** over time. Its decline is a primary C-signal. (Amplifier: recipe approval gate / attractor `hexagon`.)
- **Slow ratification** (per harness mutation): rare, permanent, high-stakes — a PR merge. Same min-not-mean discipline: promote only if it holds across the exemplar bank.

Open question (decide before scale): **new-signature minting** gets a *lighter* gate
than lint-promotion — a signature is only a join key; a bad one costs retrieval noise,
not brittleness, and unused ones can be garbage-collected. Don't bottleneck discovery.

---

## 8. Build manifest (dependency order) → Amplifier modules

| # | Asset | Realization |
|---|-------|-------------|
| 1 | Component contract / boundaries | bundle composition; judge/maker/planner as 3 isolated agent-bundles |
| 2 | Controller state machine | `tool-design-controller` (deterministic) + recipe `while/break` |
| 3 | **Lints gate — BUILD FIRST** | `tool-design-lints` (Playwright; in-page probes) |
| 4 | Judge contract | `design-judge` agent → structured JSON (score + reason + signature) |
| 5 | Planner contract | `design-planner` agent → reads ledger by signature |
| 6 | Maker contract | `design-maker` agent → rubric-blind |
| 7 | Ledger writers + schema | `tool-design-ledger` (durable cross-run) + cost from events |
| 8 | **Promotion gate — BUILD LAST** | `harness-evolution` recipe → drafts lint+test+rubric-bump PR → human merge |

**Controller shell by search width:** greedy MVP = a `recipes` convergence recipe;
beam/evolutionary = the `attractor` `loop-pipeline` (`component` fan-out, `tripleoctagon`
fan-in, retry edge = rollback, `hexagon` = escalation). Same bricks in both shells.

---

## 9. Ruthless-simplicity cut & honest status

**MVP (a true governed loop, build and stop here first):** single candidate (`width=1`)
— Observer, the seven Lints, blind Critic, minimal Planner (attack `worst_dim`, skip
`fix_status=dead`), Maker, append-only Ledger, Controller (4 stopping rules + best-so-far
+ rollback + regression veto).

**Deferred (knobs already in the schema):** beam→evolutionary width (`parent_entry_id`);
sophisticated Planner leverage model; full Pareto-front storage; multi-strategy retry.

**Status:** the diagrams *show* C; we are in **B** until (1) the cross-run ledger
persists with rejects-with-reasons + rubric SHA, and (2) **one ratchet completes
end-to-end** (a Judge catch → a lint + passing regression test, merged, firing free
next run). **C-signal:** escalation-rate per run falls while min-quality holds, and
judge-tokens per run fall.

## 10. Honest hard parts

1. **Sandboxed render of arbitrary generated HTML** — `iframe sandbox`, strict CSP, **no network / no storage** (a `network_request` is a hard lint fail: security *and* honesty); fixed viewport, pinned local fonts, animations off, wait-for-stable before capture (flaky pixels poison scores).
2. **Objective-lints-first** — the rubric is only honest because the lints anchor it; `text:chrome_ratio` and `dom_nodes` stay **gates/anchors, never scored dims** (no false precision).
3. **Taste is not fully scalar** — MACA resolves *suppression* (A-breaks-B), not a *legitimate* fork (clarity↑/character↓). That irreducible call is what the human authored `bar`/`floors` for; the escalation friction is the feature.
