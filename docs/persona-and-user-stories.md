# Page Worth — Persona & User Stories (the "coin-operated" cut)

*Working doc to decide what the design-loop app must become to be worth paying for,
not just worth demoing. Framing: imagine every "Analyze" costs the user a coin.
That single constraint changes everything — the verdict has to earn the coin, and
the result has to be good enough that they drop another one.*

---

## The value exchange, in one line

> A stranger drops in a screen they made, and 90 seconds later walks away with a
> **ranked, specific, do-this-first punch list** — and a version that's already better —
> that they'd have paid a designer $300 and three days to get.

If the output is a score and a generic paragraph, nobody pays twice. The product is
the **fix**, not the grade.

---

## Primary persona — "Maya, the solo builder shipping without a designer"

**Who she is.** Maya, 31, technical solo founder / indie hacker. Ships a SaaS side
project and a couple of client sites. Lives in Cursor, Vercel, Framer, Tailwind. Can
build anything; can't *design* anything — and she knows it. Her pages work but look
like every other AI-generated landing page: three equal feature cards, a gradient hero,
emoji bullets. "AI slop," and she can feel it, but she can't name why or fix it.

**When she shows up (triggers).**
- She just generated a landing page (v0 / Lovable / hand-rolled) and it looks *fine*
  but not *good*, and she's about to send it to real traffic.
- A launch is tomorrow. A paid ad campaign points at this page. Every hour it looks
  amateur is money lost.
- A client said "make it look more premium" and she has no vocabulary to act on it.
- A competitor's site makes hers feel cheap and she doesn't know the delta.

**Her job-to-be-done.** *"Tell me the 3 things making this look amateur, in plain
language, ranked by impact — and show me the fixed version so I can ship today."*

**What she's afraid of.**
- Wasting the coin on a vague grade she can't act on.
- Being told "it's bad" without being told *how to make it good*.
- A tool that critiques but leaves her with homework she still can't do.
- Looking dumb — she wants the *why*, phrased like a smart friend, not a rubric.

**What "worth it" means to her.** She'd happily pay a few dollars a run — or a
$12–19/mo subscription — if each run reliably hands her (a) a short, specific,
ranked fix list in her words, and (b) an actually-better version she can copy/deploy.
She'll drop coins *repeatedly*: every new page, every campaign variant, every client.

**How we know it worked.** She ships the change within the hour. She sends the
before/after to her cofounder to prove she leveled up. She comes back next launch.

### Why Maya and not someone else
She has **high, recurring, self-inflicted pain**, **money**, **no designer**, and a
**fast path to act** (she can edit HTML/deploy in minutes). That's the sharpest wedge
for a pay-per-use design critique that *also hands back a better artifact*.

### Adjacent personas (serve later, design for now-compatible)
- **Devon, the agency/freelance dev** — runs client sites; wants a shareable,
  white-label-ish verdict to justify design changes to clients. Higher willingness to
  pay, wants export + branding.
- **Priya, the PM/marketer** — owns a landing page, can't code. Loves the *diagnosis*
  but needs the fix handed to a dev or a no-code tool. Wants the punch list, not the HTML.
- **Sam, the design-curious student** — wants to *learn* the eight dimensions. Great for
  virality and the free tier; low direct revenue.

### Who we are explicitly NOT for (keeps the product honest)
Design systems teams, enterprises with brand guidelines, Figma-native designers who
already know what's wrong. They want depth/governance, not a coin-op punch list.

---

## User stories

*Written as `As Maya, I want … so that …`, grouped by the coin-operated funnel. Each
stage is a place she can bounce (and not pay) if it's weak.*

### 1 — Land & trust (before she spends the coin)
1. As Maya, I want to instantly understand what I'll get for my money, so that I'm not
   gambling a coin on a black box.
2. As Maya, I want to see one real example verdict (a sample before/after) without
   paying, so that I trust the output is specific and not generic.
3. As Maya, I want to know the price and what a "run" includes *before* I start, so that
   there are no surprises.
4. As Maya, I want proof this critiques *my* page and isn't a canned demo, so that I
   believe the result is about me.

### 2 — Give it my screen (input)
5. As Maya, I want to paste my live URL and have it capture the page itself (full-page,
   correct viewport), so that I don't have to screenshot manually.
6. As Maya, I want to drop a screenshot or paste HTML, so that I can critique work that
   isn't deployed yet.
7. As Maya, I want to pick the viewport (mobile vs desktop), so that I'm judged on how
   users actually see it.
8. As Maya, I want to add one line of context ("this is a B2B pricing page"), so that the
   critique is judged against the right goal.
9. As Maya, I want it to just work if I fat-finger the input, so that I don't waste a coin
   on a failed run.

### 3 — Watch it think (the run)
10. As Maya, I want to feel progress and momentum, not a spinner, so that the wait feels
    like work being done for me.
11. As Maya, I want the run to feel *fast* (seconds, not a slow scripted crawl), so that
    the coin feels well spent.
12. As Maya, I want to stop a run I don't care about, so that I don't feel trapped.
13. As Maya, I want to trust that a stopped/failed run doesn't cost me a coin, so that I
    experiment freely.

### 4 — Get the verdict (the payload — this is what she paid for)
14. **As Maya, I want the top 3 problems with my page, ranked by impact, in plain
    language, so that I know exactly what to fix first.** *(the core promise)*
15. As Maya, I want each problem paired with the *specific fix* (and ideally the exact
    copy/markup change), so that I can act without a designer.
16. As Maya, I want the "why" behind each problem in a smart-friend voice, so that I learn
    and trust it.
17. As Maya, I want a believable before/after where I can see *what changed and why*, so
    that I trust the upgrade instead of squinting at two iframes.
18. As Maya, I want a one-glance verdict (is it good enough to ship?), so that I get a
    yes/no, not just a number.
19. As Maya, I want the score to mean something I can explain to my cofounder, so that it's
    ammunition, not trivia.

### 5 — Take the value with me (the deliverable)
20. **As Maya, I want to copy or download the improved HTML, so that I can ship it in
    minutes.** *(the thing that makes a coin turn into a subscription)*
21. As Maya, I want the punch list as copy-pasteable text / a Cursor-ready prompt, so that
    I can apply fixes to my real codebase.
22. As Maya, I want a shareable link to the before/after + verdict, so that I can send it
    to my cofounder or client (and it markets the tool for me).
23. As Maya, I want a fallback deliverable even when it "escalates" (couldn't fully fix it),
    so that I never pay a coin and leave empty-handed.

### 6 — Steer & iterate (spend more coins on purpose)
24. As Maya, I want to re-run asking it to focus on one dimension ("fix restraint"), so
    that I can direct the next pass.
25. As Maya, I want to try a couple of directions and pick the winner, so that I have
    agency, not one forced answer.
26. As Maya, I want to feed my edited version back in and see the score move, so that I get
    a tight iterate-measure loop.
27. As Maya, I want to compare against a competitor's page, so that I can close a specific gap.

### 7 — Come back (retention & the business)
28. As Maya, I want my runs saved to *my* account across devices, so that history is mine,
    not this browser's.
29. As Maya, I want to buy coins in a pack or subscribe, so that I stop thinking about
    per-run cost once I'm hooked.
30. As Maya, I want to see my pages improve over time (scores climbing), so that I feel the
    tool is making me better.
31. As Maya, I want a nudge when I ship a new page ("want a check?"), so that it becomes a
    habit, not a one-off.

---

## Gap analysis — what exists vs. what a paying Maya needs

Mapped against the current app (single smart input → streamed transcript → 8-dim score →
before/after → full report → local history; **DRY-scripted**, real backend unproven).

| # | Story | Status today | The gap that blocks the coin |
|---|-------|--------------|------------------------------|
| 1–3 | Understand value / see sample / know price | ❌ Missing | No pricing, no free sample, no "what you get" framing. |
| 4,11 | Real critique of *my* page, fast | ⚠️ Faked | DRY mode returns a scripted 29/32 regardless of input; real backend unproven. **You cannot charge for this yet.** |
| 5,7 | Capture live URL / choose viewport | ⚠️ Partial | URL is accepted but (in dry) never actually rendered; no viewport choice, no full-page capture. |
| 6 | Screenshot / HTML input | ✅ Have | Works well now. |
| 8 | Add goal/context | ❌ Missing | Backend has a `prompt`/`task_class` notion but the UI never asks. Critique can't be goal-aware. |
| 9,13 | Fault-tolerant input / no charge on failure | ⚠️ Partial | Graceful disabled states, but no coin/credit model to protect. |
| 10 | Momentum during run | ✅ Have | Pass N/3 bar + streamed log — this part is already good. |
| 12 | Stop a run | ✅ Have | Just built. |
| **14** | **Top-3 ranked problems in plain language** | ⚠️ Buried | The data exists (`fix_batch`, worst-dimension) but the **verdict leads with a score + generic paragraph**, not a ranked punch list. This is the #1 product gap. |
| **15** | **Each problem → specific fix / exact change** | ⚠️ Buried | `fix_batch` has issue+fix per pass, but it's hidden in the full report, not surfaced as the headline deliverable. |
| 16 | "Why" in a human voice | ⚠️ Partial | Copy exists but is rubric-flavored, not smart-friend. |
| 17 | Before/after with *what changed & why* | ⚠️ Partial | Two thumbnails side by side — no diff, no annotations, no "we cut X, added Y." She has to guess. |
| 18,19 | One-glance ship/no-ship + explainable score | ⚠️ Partial | Badge + score exist; no crisp "ship it / don't" call. |
| **20** | **Copy/download the improved HTML** | ❌ Missing | The upgraded page is viewable/openable but there's **no export/copy/deploy** — the single biggest "why subscribe" lever is absent. |
| **21** | **Punch list as text / Cursor-ready prompt** | ❌ Missing | No copy-to-clipboard, no "apply-in-your-codebase" prompt. |
| 22 | Shareable result link | ❌ Missing | Results live in-session; history links are local file paths, not shareable URLs. Kills virality. |
| 23 | Fallback deliverable on escalate | ❌ Missing | Escalated = "a human should take it from here" → she paid and got told *no*. Unacceptable coin-op outcome. |
| 24 | Re-run focused on one dimension | ❌ Missing | Re-run exists but can't be *steered*; no options passed. |
| 25 | Try directions / pick a winner | ❌ Missing | One forced answer; the loop's own candidate variants aren't exposed to choose from. |
| 26 | Feed edited version back, watch score move | ⚠️ Partial | Re-run reuses the same input; no "new version, same critique, delta vs last." |
| 27 | Compare against a competitor | ❌ Missing | No A-vs-B of two different pages. |
| 28,30 | My account / progress over time | ❌ Missing | History is a local `history.jsonl` — not auth'd, not cross-device, not "mine." |
| 29,31 | Buy coins / subscribe / habit nudges | ❌ Missing | No billing, no accounts, no re-engagement — no business model wired at all. |

---

## The synthesis — what's actually missing to make it coin-worthy

Three things separate today's demo from something Maya pays for twice:

**1. The payload is a grade; it needs to be a punch list.** Everything Maya paid for —
the ranked "here are your 3 problems and the exact fix for each, in my words" — already
exists as *data* (`fix_batch`, worst-dimension per pass) but is buried inside the full
report. **Lead Results with the ranked, specific, do-this-first punch list.** The score
and before/after become supporting evidence. This is a re-prioritization of what's on
screen, not new ML — the highest-leverage change available.

**2. She has to be able to *take* the value.** No export, no copy, no shareable link. A
coin-op tool must hand her something pocketable: copy the improved HTML, copy the punch
list as a Cursor prompt, and a share link that doubles as marketing. Without this,
there's no reason to subscribe and no viral loop.

**3. It has to actually be about her page.** DRY mode is perfect plumbing and a great
demo, but you cannot charge for a scripted 29/32 that ignores the input. The real backend
(and real URL capture + viewport + goal context) is the difference between a toy and a
service. And the "escalate" path must always still hand back *something* — never take a
coin and say "no."

**Everything else** (accounts, billing, focused re-runs, competitor compare, progress
over time) is real and worth doing — but it's the *second* coin. The first coin is won or
lost on: **ranked fixes up front, a deliverable she can take, and a critique that's
genuinely hers.**
