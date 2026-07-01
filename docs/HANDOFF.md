# Design Loop web app — handoff

**Date:** 2026-07-01
**Repo:** `michaeljabbour/amplifier-bundle-design-loop` (branch `main`)
**App:** `app/` — FastAPI + WebSocket backend, vanilla-JS single-page front end
**Run:** `./run.sh` → http://localhost:8010 (DRY mode by default — zero cost)

This document is the single source of truth for the work done in this session: what
changed, why, where, how it was verified, and what's still open. It's written so a new
engineer can pick it up cold.

---

## 1. TL;DR — what this became

The app started as a working-but-clunky demo of the design-loop pipeline (upload a
screen → streamed transcript → score → embedded report). Over this session it became a
**product-shaped design-review tool** whose Results screen feels like handing your page
to a senior design lead:

- One **smart input** (auto-detects URL / HTML / screenshot) with optional **Goal**,
  **Audience**, and **Compare-URL** context.
- A live **Working** view with a pass counter, progress bar, and **Stop**.
- A **Results** screen that leads with a **ranked punch list** (issue → fix, by
  impact × effort), a **ship / not-ready verdict**, **what's working**, a **root cause**,
  a **real accessibility & ground-truth audit of your actual page**, a **competitor
  benchmark**, an **annotated view of your real markup**, before/after, a scorecard, and
  **deliverables** (copy fixes as a prompt, copy/download the improved HTML, share link).
- **Steering**: re-run, focus a dimension, and a **score delta vs. the last run**.
- Honest run bookkeeping: **one id / one directory per run**, and a **DRY/LIVE mode
  badge** driven by a preflight check.

Everything was verified by driving the running app in a real (headless Chromium)
browser and capturing screenshots — see [§6](#6-verification) and
[docs/screenshots/](./screenshots).

---

## 2. How to run

```bash
cd ~/dev/amplifier-bundle-design-loop
./run.sh                      # DRY mode (default), http://localhost:8010
```

DRY mode streams a scripted, zero-cost transcript **but still runs the real
deterministic ground-truth audit** on your actual HTML/URL. To use the real subjective
critic (spends LLM tokens):

```bash
# one-time: install the foundation bundle into the app venv
uv pip install --python .venv/bin/python amplifier-foundation   # see app/real_runner.py
DESIGN_LOOP_DRY=0 ./run.sh
```

Check which backend a run will use:

```bash
curl -s localhost:8010/api/preflight | python -m json.tool
```

The landing page shows a **● DRY · FREE** / **● LIVE** / **⚠ LIVE · not installed** badge
reflecting the same preflight.

---

## 3. Architecture at a glance

```
Browser (vanilla JS SPA, built in app/landing.py)
   │  POST /api/upload | /api/source        → creates run dir + meta.json
   │  WS  /ws  {type:"start", run_id, options}
   ▼
app/ws_handler.py   (cancellable run task; routes dry vs real; forwards result)
   ├── app/dry_runner.py    scripted transcript + REAL audit  (DESIGN_LOOP_DRY=1)
   └── app/real_runner.py   loads bundle, runs recipe, + REAL audit  (DESIGN_LOOP_DRY=0)
         │
         ├── app/audit.py     deterministic ground-truth (static + browser lints)
         ├── app/annotate.py  redline overlay injected into the user's real HTML
         └── app/results.py   build_result_payload(): punch list, verdict, scores…
                                 ↑ reuses tool-render-report vocabulary
   ▼
render_report.template.render()  → runs/<id>/{baseline,upgraded,report}.html
Results screen consumes the WS `result` payload (see §5).
```

Durable output + history: `~/Downloads/design-loop/runs/<run_id>/` and
`~/Downloads/design-loop/history.jsonl` (one id/dir per run — reconciled this session).

---

## 4. What changed — by theme

### 4.1 Original workflow rough edges (the first six)

| # | Fix | Where |
|---|-----|-------|
| 1 | **Single smart input** replacing the 3-mode segmented control + per-panel Analyze buttons. Auto-detects URL/HTML/image; Enter / ⌘-Enter / drop / paste all start a run. | `app/landing.py` |
| 2 | **Connected journey + progress**: Landing→Working→Results auto-advance, step icons turn to checks, "Pass N / 3" counter + determinate progress bar. | `app/landing.py`, `app/dry_runner.py` (emits `Pass N/M`) |
| 3 | **Concise Results** replacing the recursive full-report iframe: verdict + real before/after (scaled thumbnails) + full report behind a link. | `app/landing.py` |
| 4 | **Cancel / re-run**: run executes as a cancellable task; **Stop** button; **Re-run** reuses the same run id/dir. | `app/ws_handler.py`, `app/landing.py` |
| 5 | **One id / one dir per run**: dry records now carry the app's `run_id`; the report renderer's durable copy is skipped when it would duplicate. History + WS result + on-disk dir now all agree. | `app/dry_runner.py`, `modules/tool-render-report/.../template.py` |
| 6 | **DRY variants**: converged (29/32, `bar_met`) and escalated (18/32, `plateau`) transcripts, auto-alternating per run so both terminal states are demoable. | `app/dry_runner.py` |

### 4.2 Product value layer (make it worth a "coin")

Grounded in [docs/persona-and-user-stories.md](./persona-and-user-stories.md):

- **Ranked punch list first** — top problems as *issue → specific fix*, not a grade.
- **Deliverables** — Copy fixes as a Cursor-ready prompt, Copy improved HTML, Download
  HTML, Copy share link, Open full report.
- **Steering** — Re-run, Focus a weak dimension, and a **score delta vs. last run**.

Files: `app/results.py` (new payload), `app/landing.py` (Results rebuild),
`app/dry_runner.py` / `app/real_runner.py` / `app/ws_handler.py` (threading).

### 4.3 Senior-review upgrade

Grounded in [docs/senior-design-lead-workflow.md](./senior-design-lead-workflow.md):

- **Intent-first**: optional **Goal** + **Audience**, echoed and made goal-aware
  ("For a B2B pricing page, the highest-impact fix is …").
- **What's working** (strengths, or an honest "nothing clears competent yet — pure
  upside").
- **Root cause** — the one-line through-line a lead would name.
- **Impact × effort** ranking with a **"Do this first"** call, not just severity.
- **Accessibility & ground truth** — a **real, deterministic, no-LLM audit of the actual
  page**: static checks (viewport meta, lang, title, heading order, alt text, form
  labels, vague links, "slop signals") + browser lints reused from the bundle's own
  `tool-design-lints.run_lints` (WCAG contrast, keyboard focus, viewport overflow).

Files: `app/audit.py` (new), `app/results.py`, `app/landing.py`, runners.

### 4.4 Loop improvements (this session's final batch)

1. **Audit is real inside the loop** — objective fails (contrast, viewport, alt,
   overflow) become first-class punch-list items and **veto the ship decision**: a page
   with 1.9:1 contrast reads *Not ready — N blocking issues* even at 29/32. Mirrors the
   loop's own "deterministic lints anchor subjective scores" philosophy.
2. **Benchmark vs a competitor URL** — the same deterministic audit run on a competitor,
   shown *You vs. Them* per check (objective-only; noted as such).
3. **Annotate the actual page** — `annotated.html` injects numbered redline markers +
   a legend onto the user's real markup ("Your page, annotated").
4. **Real-backend preflight** — `GET /api/preflight` + a DRY/LIVE **mode badge**.

Files: `app/audit.py`, `app/annotate.py` (new), `app/results.py`, `app/main.py`
(`/api/preflight`), `app/landing.py`, runners, `app/ws_handler.py`.

---

## 5. Data model (WS protocol additions)

The `stream_event` / `tool:pre` / `tool:post` / `display` protocol is unchanged. The
`result` message was extended (backward-compatible additions):

**WS `start` options** (client → server): `{ context, audience, compare_url, focus, variant }`

**WS `result`** (server → client):
```
{ type:"result", run_id, report_url, upgraded_url, baseline_url, annotated_url,
  total, converged, verdict, variant, payload }
```

**`payload`** (built by `app/results.py::build_result_payload`):
```
problems: [ { criterion, label, a, b, issue, fix, severity,
              impact, effort, first, source?, blocker? } ]   # audit fails first
scores:   [ { id, label, a, b, delta } ]                     # 8 dims, before→after
improved / regressed: [label, …]
strengths: [ { label, a, note } ]   strengths_note: str
root_cause: str
total, bar, ship (bool), ship_label, blockers (int), blocker_note
context, audience, goal_note, reason
ground_truth: { available, findings:[{id,label,status,detail}], summary:{pass,warn,fail}, note }
benchmark?:   { url, available, you, them, you_findings, them_findings, note }
has_annotated?: bool
```

**New message type:** `{ type:"cancelled", run_id }` (Stop / disconnect).
**New endpoint:** `GET /api/preflight` → `{ dry_mode, foundation_installed, real_available, mode, message }`.

---

## 6. Verification

The mounted `.venv` is macOS/Python-3.12, so it can't run in a Linux sandbox. Changes
were verified by standing up the app in a throwaway Linux venv and **driving the live
app with headless Chromium (Playwright)** — real navigation, real WebSocket, real
screenshots — plus the module unit tests.

Verified end-to-end:
- All three inputs via auto-detect; no console errors.
- Converged **and** escalated states (auto-alternate).
- **One dir per run**, history ids match the run dirs (issue #5 fixed — before: two dirs).
- Stop halts mid-run; Re-run reuses the input; Start-over resets; history opens (report 200).
- Mobile (390 px) layout holds; input autofocus on load.
- Punch list, deliverables (download filename, absolute share link, prompt text),
  focused re-run + delta.
- Ground-truth audit catches a planted **1.9:1 contrast fail**, missing viewport, and
  missing alt on real markup; blocking fails flip the ship verdict.
- Benchmark renders *You vs. Them* against a real URL; annotated page serves with markers.
- Preflight endpoint + mode badge.
- `modules/tool-render-report` tests: **29 passed** (template + verdict).

Screenshots (before → after) live in [docs/screenshots/](./screenshots):

| Shot | What it shows |
|------|---------------|
| `before_01_landing.png`, `before_03_results.png` | Original clunky landing + the recursive report iframe. |
| `after_01_landing.png` | Single smart input, mode badge, step icons. |
| `after_03_working_progress.png` | Pass N/3 + progress bar + Stop, connected steps. |
| `after_04_results_converged.png` / `after_05_results_escalated.png` | Verdict + before/after, both terminal states. |
| `after_07_stopped.png` | Cancel mid-run. |
| `after_10_mobile_results.png` | Mobile layout. |
| `after_11_results_punchlist.png` | Ranked punch list + deliverables + scorecard. |
| `after_13_senior_results.png` | Goal/audience, root cause, impact×effort, ground-truth audit. |
| `after_14_loop_upgrades.png` | Audit-real blockers, benchmark, annotated page, mode badge — all together. |

---

## 7. File-by-file change map

**New files**
| File | Lines | Role |
|------|-------|------|
| `app/results.py` | 316 | `build_result_payload()` — punch list, verdict, strengths, root cause, impact×effort, audit merge + ship veto. |
| `app/audit.py` | 321 | Deterministic ground-truth audit: static stdlib checks + browser lints via `tool-design-lints.run_lints`. |
| `app/annotate.py` | 106 | Injects the redline overlay into the user's real HTML → `annotated.html`. |
| `docs/persona-and-user-stories.md` | 213 | Persona (Maya) + coin-operated user stories + gap analysis. |
| `docs/senior-design-lead-workflow.md` | 166 | Senior-lead review recipe, scored vs. our workflow, with shipped-updates. |
| `docs/README.md` | 25 | Docs index. |
| `docs/HANDOFF.md` | — | This document. |

**Modified files**
| File | Δ | Role of changes |
|------|---|-----------------|
| `app/landing.py` | ~+590 | Whole front end: smart input, goal/audience/compare fields, progress, Stop/Re-run, Results rebuild (punch list, deliverables, ground truth, benchmark, annotated, scorecard, steer), mode badge. |
| `app/dry_runner.py` | ~+250 | Variants, run_id stamping, focus, context/audience, ground-truth audit + benchmark + annotate wiring, payload. |
| `app/ws_handler.py` | ~+60 | Cancellable run task, cancel message, option threading (context/audience/focus/variant/compare_url), result payload + `annotated_url`. |
| `app/real_runner.py` | ~+50 | Same payload + audit + benchmark + annotate for the real backend. |
| `app/main.py` | ~+45 | `GET /api/preflight`. |
| `modules/tool-render-report/.../template.py` | ~10 | Skip the durable self-copy when out_dir == durable dir (issue #5). |

Net (tracked): **+1107 / −330** across 6 files, plus the new modules above.

---

## 8. Docs index

- [docs/README.md](./README.md) — index of all docs.
- [docs/persona-and-user-stories.md](./persona-and-user-stories.md) — who we serve + backlog + gaps.
- [docs/senior-design-lead-workflow.md](./senior-design-lead-workflow.md) — the review recipe + closeness scoring.
- [docs/HARNESS_DESIGN.md](./HARNESS_DESIGN.md), [docs/PRIMITIVE.md](./PRIMITIVE.md) — the governed-loop architecture (background).

---

## 9. Known limitations & next steps

**Constraints honored:** Page_Worth vendored CSS (`t._PW_*`) kept; the
`stream_event`/`tool:pre`/`tool:post`/`display` protocol kept; DRY mode still zero-cost;
SPA never navigates away; `landing.py` JS remains string-concatenation (no backticks).

**Open / deferred:**
1. **Real subjective critique** on the user's own page needs `amplifier_foundation` +
   tokens (`DESIGN_LOOP_DRY=0`). The path is wired and preflighted but **not run/verified
   in-sandbox** — do a live smoke test before relying on it. See `app/real_runner.py`.
2. **Benchmark is objective-only** — a competitor's subjective 8-dimension score still
   needs the critic; today we compare ground-truth checks and say so.
3. **Annotation covers HTML input** (and could be extended to URL by fetch+inject);
   image input has no markup to annotate.
4. **DRY scores are still scripted** for the subjective dimensions — only the ground-truth
   half is real in DRY. The audit-derived blockers are real; the 8-dim taste scores are not.
5. **Accounts / billing / pricing** were intentionally **out of scope** (per direction).

**Natural next steps:** (a) live-verify the real backend with the mode badge; (b) promote
recurring ground-truth findings into the loop's real lints (the "promotion ratchet" in
`docs/HARNESS_DESIGN.md`); (c) extend annotation + benchmark to fetch URLs server-side.

---

## 10. Quick reference

```
Endpoints:  GET /  ·  GET /health  ·  GET /api/preflight  ·  GET /api/history
            POST /api/upload  ·  POST /api/source  ·  WS /ws  ·  static /runs
Env:        DESIGN_LOOP_DRY=1 (default, free)  |  =0 (real critic, tokens)
            PORT=8010
Output:     ~/Downloads/design-loop/runs/<run_id>/{baseline,upgraded,report,annotated}.html
            ~/Downloads/design-loop/history.jsonl
Tests:      (cd modules/tool-render-report && pytest tests/test_template.py tests/test_verdict.py)
```
