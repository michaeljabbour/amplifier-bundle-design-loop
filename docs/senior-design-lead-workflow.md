# How a senior design lead reviews a site — and how close we are

*Companion to `persona-and-user-stories.md`. If Maya is who we serve, the bar for
quality is: does a run feel like handing your page to a seasoned design director for a
crit? This maps the recipe an experienced lead actually runs, then scores our current
workflow against each stage so the gaps are concrete.*

> **Update — shipped this session (after studying the loop internals).** Several
> front-half gaps are now closed in the app layer, grounded in the loop's real
> vocabulary (`tool-design-lints` metrics, the critic's dimension definitions,
> the controller's gate reasons):
> - **Intent-first (stage 0):** Goal *and* Audience are captured and the verdict is
>   goal-aware ("For a B2B pricing page, the highest-impact fix is restraint").
> - **Balance + root cause + impact×effort (stages 4,5,7):** Results now leads with
>   "What's working," names a one-line **root cause**, and ranks the punch list by
>   **impact × effort** with a "Do this first" call — not just severity.
> - **Accessibility + ground truth (stage 2):** a real, deterministic, no-LLM audit
>   runs on the user's **actual markup/URL** — WCAG contrast (via the bundle's own
>   `run_lints`), keyboard focus, viewport overflow, plus static checks (viewport
>   meta, lang, title, heading order, alt text, form labels, link text, and "slop
>   signals" that map to the critic's `restraint` definition). This works even in
>   DRY mode because it's ground truth, not LLM inference.
>
> **Second pass — also now shipped:**
> - **Audit is real *inside* the loop:** objective ground-truth fails (contrast,
>   viewport, alt, overflow) are folded into the punch list as first-class problems
>   and **veto the ship decision** — a page with 1.9:1 contrast reads "Not ready,
>   blocking issues" even at 29/32. Exactly what a lead does: won't sign off on an
>   unreadable page regardless of taste.
> - **Benchmarking (stage 3):** optional "compare to this URL" runs the same
>   deterministic audit on a competitor and shows yours-vs-theirs, per check.
> - **Annotate the actual page (stage 6 evidence):** "Your page, annotated" renders
>   the user's real markup with numbered redline markers + a legend, pointing at
>   where each problem is.
> - **Real-backend preflight:** `/api/preflight` + a DRY/LIVE mode badge; opting into
>   `DESIGN_LOOP_DRY=0` gives a clear up-front signal instead of a mid-run error.
>
> Still open / blocked: benchmarking is **objective-only** (subjective 8-dimension
> scoring of a competitor still needs the critic), and running the **real subjective
> critique** on the user's own page needs `amplifier_foundation` + tokens
> (`DESIGN_LOOP_DRY=0`) — wired and preflighted, but not run/verified in-sandbox.
> The stage table below is the original pre-session assessment, kept for reference.

---

## The recipe a senior design lead actually runs

A good design director doesn't "look and react." They run a repeatable process. Roughly:

**0. Gather intent before looking at pixels.** *"What is this, who's it for, what's the
one job of this page, what stage are you at, and what were you going for?"* They refuse
to critique in a vacuum — everything is judged **relative to the goal, audience, and
brand**. A pricing page and a landing page get different reviews.

**1. Five-second gut read.** Squint at it. What's the focal point? Is the hierarchy
obvious? Is it clear what to do? Does it feel credible/premium or generic and templated?
What's the emotional read? They note the first impression before rationalizing it.

**2. Systematic heuristic pass.** Walk the standard dimensions a design org shares:
message/value-prop clarity, visual hierarchy, information architecture, layout & grid,
spacing rhythm & alignment, typography (scale, pairing, legibility), color & **contrast/
accessibility (WCAG)**, consistency & design-system adherence, brand expression & point
of view, content/copy quality & tone, **interaction affordances & states** (hover, focus,
empty, error, loading), the **primary CTA & conversion friction**, **responsive/mobile**
behavior, motion appropriateness, trust signals, and performance/perceived speed.

**3. Benchmark against references.** *"How does this stack up against [competitor], our
design system, and best-in-class patterns?"* Relative, not absolute.

**4. Diagnose root causes, not symptoms.** Connect the dots: "these six nitpicks all
trace back to *no type scale* and *no focal point*." Separate systemic issues from polish.

**5. Prioritize by impact × effort.** *"If you fix one thing, fix this."* A short P0 list,
not 40 comments. High-impact-low-effort first.

**6. Give specific, actionable direction with rationale — and show, don't tell.** Not
"make it pop" but "cut to one CTA, set a 1.25 type scale, kill the gradient." Point at
*where* on the page (redlines/annotations), cite examples, sometimes sketch the fix.

**7. Balance — call out what's working.** Lead with strengths too, so the designer keeps
what's good and trusts the critique.

**8. Frame as a conversation and teach.** Ask intent first, explain the *principle* so the
designer levels up, not just this one page.

**9. Assign next steps and re-review.** Concrete actions, an owner, and a checkpoint to
confirm it actually improved.

**10. Make a ship call.** Explicit gate: ship / iterate / block, with the reason.

---

## Our workflow vs. the recipe, stage by stage

*"Today" reflects the app after this session's changes: single smart input + optional
goal, streamed 8-dimension governed loop, and a Results screen that leads with a ranked
punch list (issue→fix), a ship/no-ship verdict, before→after redesign + scorecard,
copy-as-prompt / copy-HTML / download / share, and focused re-runs with a score delta.*

| Stage (what a lead does) | What we do today | Closeness | The gap |
|---|---|---|---|
| **0. Gather intent** (goal, audience, brand, stage, device) | Optional one-line "Goal" field | ⚠️ Partial | We ask for *goal* only, and in DRY it doesn't actually change the critique. No audience, brand, stage, or device. No "what were you going for?" |
| **1. Five-second gut read** | Ship verdict + score + one-line takeaway | ✅ Strong | Close. Missing the *emotional/credibility* read ("feels generic vs. premium"). |
| **2. Heuristic pass** | 8 dimensions: clarity, elegance, restraint, empowerment, agency, ease, character, point | ⚠️ Partial | Covers message/hierarchy/restraint/voice well, but **no accessibility, no responsive, no interaction-states, no content/copy, no performance, no trust-signals** pass. And the taxonomy is bespoke, not the standard vocabulary a design org uses. |
| **3. Benchmark vs. references** | None | ❌ Missing | No competitor compare, no design-system/brand check, no "best-in-class pattern" reference. A lead always benchmarks. |
| **4. Root-cause diagnosis** | Per-dimension issue+fix in the punch list | ⚠️ Partial | We name the top problems, but don't *connect* them ("all of this traces back to no type scale + no focal point"). |
| **5. Prioritize by impact × effort** | Top-3 ranked punch list | ⚠️ Partial | Ranked by **severity of the problem**, not **impact × effort**. No "high-impact, low-effort, do this first" framing. |
| **6. Specific direction + show don't tell** | Issue→fix per problem, copy-as-Cursor-prompt, **and an actual redesigned page (before/after)** | ✅ Strong | This is our superpower — most leads *describe* the fix; we *produce* a better version. Gap: we don't **point at where** on their page (no annotations/redlines on the actual screenshot). |
| **7. Balance — what's working** | "What changed" chips (about the upgrade) | ❌ Missing | We never tell the user what their *input* already does well. Crits that only list problems feel punishing. |
| **8. Conversation + teach** | The "why" in each fix, in a smart-friend voice | ⚠️ Partial | We teach the fix, but never ask intent first, and the "principle" behind each dimension isn't surfaced. |
| **9. Assign + re-review** | Re-run + **focused re-run** + **score delta vs last run** | ✅ Strong | Genuinely close — you can act, re-submit, and watch the score move. Missing: a saved checklist of "did you do these?" |
| **10. Ship call** | Explicit "Ready to ship / Not ready yet" vs the bar | ✅ Strong | Close. Could add "ship, but fix X first" as a middle gate. |
| **(cross-cutting) Review the *real* artifact** | DRY = scripted; real backend unproven | ⚠️ Blocked | A lead reviews *your actual page*. Until the real backend + live URL capture is on, the critique isn't truly yours. |

**Scoreboard:** Strong on 4 (gut read, actionable direction + redesign, assign/re-review,
ship call), Partial on 5 (intent, heuristics, root-cause, prioritization, teach), Missing
on 2 (benchmarking, what's-working), Blocked on 1 (real critique of the actual page).

---

## Where we're genuinely close — and where a lead would still out-review us

**We nailed the *output* half of a senior review.** The back end of a crit — prioritized
top issues, specific fixes with rationale, a ship call, and crucially a *produced redesign*
you can take and re-review with a score delta — is now here, and the redesign actually
goes *beyond* what most leads deliver (they talk; we build). Stages 1, 6, 9, 10 feel like a
real director.

**We're still thin on the *front* half of a review — the part that makes a critique
trustworthy and senior:**

1. **Intent-first, relative-to-goal review (stage 0).** A lead spends the first five
   minutes on context and never critiques absolutely. We ask one optional line and, in
   DRY, ignore it. *Highest-leverage non-billing fix:* make the critique visibly
   goal-aware — capture audience + primary goal + stage, echo them, and let them reframe
   the punch list ("for a pricing page, your weakest link is trust, not character").

2. **Accessibility + responsive + interaction states (stage 2).** No senior review ships
   without a contrast/WCAG check, a mobile pass, and a look at hover/focus/empty/error
   states and the actual CTA friction. We do none. This is table stakes for "professional
   review," and much of it (contrast, tap targets, alt text, viewport render) is
   *mechanically checkable* — high-credibility, not even LLM-hard.

3. **Benchmarking (stage 3).** Leads are relative thinkers: vs. competitors, vs. the design
   system, vs. best-in-class. We're an island. A "compare against this URL" mode and/or a
   brand/design-system input would close this.

4. **Balance + root cause + impact×effort (stages 4,5,7).** Lead with one or two things
   that *work*; connect the problems to a shared root cause; and rank by impact×effort, not
   just severity. These are re-framings of data we *already have* — cheap, and they're the
   difference between "a rubric ran" and "a director looked at this."

5. **Point at the page (stage 6 evidence).** We describe and we redesign, but we don't
   annotate *their* screenshot ("this hero, right here, has no focal point"). Redlines on
   the actual input are what make a crit feel authoritative.

6. **The real-artifact gap (cross-cutting).** Everything above is theater until the
   critique is actually of *their* page. The real backend + live URL/full-page capture at
   a chosen viewport is the unlock that turns all of this from "convincing" into "true."

**Bottom line:** we've gone from *grade* to *credible junior reviewer who also hands you a
redesign*. To feel like a **senior design lead**, the missing moves are, in order:
(1) make it genuinely goal/audience-aware, (2) add the accessibility + responsive +
interaction pass, (3) let it benchmark against a reference, (4) reframe the verdict with
strengths + root cause + impact×effort, (5) annotate the actual page — and underneath it
all, (6) run the real critique on the real artifact.
