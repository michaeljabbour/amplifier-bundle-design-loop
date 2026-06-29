# Signature Vocabulary

A **signature** is a controlled join key that links a recurring defect — as observed
by the Critic — to the history of fix attempts recorded in the Ledger.
Format: `<problem>:<region>`.

- `<problem>` — a slug naming the observable defect (kebab-case, imperative-negative).
- `<region>` — the page zone where the defect lives, or `any` if zone-independent.

Signatures are **governed capital**: they key cross-run memory. A bad join key costs
retrieval noise; a missing one means the Planner cannot skip dead fixes. Treat the
vocabulary accordingly.

---

## Canonical entries

| Signature | Defect description |
|---|---|
| `low-contrast-cta:landing` | CTA button or link fails WCAG AA contrast against its background on the landing region |
| `gradient-slop:any` | Purple-to-blue (or similar generic) gradient used anywhere on the page |
| `default-font:any` | Inter, Roboto, or another default system font chosen with no deliberate typographic reason |
| `generic-hero:landing` | Hero section uses centered text on a full-bleed image or gradient — the most common slop default |
| `buzzword-copy:any` | Headline or body copy reads as AI-generated marketing filler with no specificity or voice |
| `equal-card-grid:any` | Cards laid out in a uniform grid with identical visual weight — no hierarchy, no emphasis |
| `focus-trap:modal` | Modal or overlay is reachable but keyboard focus does not cycle within it, or close is unreachable |
| `dom-bloat:list` | List or feed region contains excessive DOM nodes (>500 in the visible viewport subtree) |
| `no-hierarchy:any` | The page lacks a clear typographic or spatial hierarchy — all elements compete equally |
| `centered-everything:any` | All or nearly all text and elements are center-aligned, removing reading flow and directional cues |
| `weak-affordance:cta` | Primary call-to-action is not immediately recognisable as interactive — blends into surrounding content |
| `tone-mismatch:any` | Visual tone (colours, imagery, spacing) contradicts the stated product personality or audience |

---

## Governance rule

**Proposing a new signature**: a Critic may propose a signature not listed above by
including `"unratified": true` in its `signatures` array entry. Example:

```json
{"dim": "character", "signature": "stock-photo-hero:landing", "unratified": true}
```

An unratified signature is a **discovery, not a join key** — the Ledger records it,
but the Planner MUST NOT query dead-fixes against it until it is ratified.

**Ratification requires** a pull-request to this file adding the entry to the canonical
table above, with at least one supporting Ledger example. Human merge = ratification.
Unused unratified signatures may be garbage-collected from the Ledger without ceremony.

The ratification gate is intentionally lighter than lint-promotion (§6 of
HARNESS_DESIGN.md): a bad signature costs retrieval noise, not brittleness. Do not
bottleneck discovery.
