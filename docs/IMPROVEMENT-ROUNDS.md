# Taste and Design Loop: one bounded improvement record

Taste owns the human-judgment method and canonical improvement-round/v1 schema. Design Loop owns the optional deterministic ledger, score controller, recipe and report adapter. Their jobs remain separate: technical validity and score rank do not decide human adoption.

The canonical portable schema is `skills/improve-taste-and-elegance/references/improvement-round.schema.json` in the Taste repository. This consumer retains a byte-identical, hashed contract snapshot under `contracts/`, with its MIT notice and provenance. It does not require Taste, Memory, a service or model to validate a round.

`amplifier_module_tool_design_ledger.improvement_round.validate_round` checks one record and returns technical validity, blocked gates, recorded keep/undo/pending, remaining-round status and stop reason. The ledger also prevents a new round resetting or silently raising its recorded run budget. It rejects critical failed/unknown keep decisions, a changed brief/baseline/candidate under the same round ID, missing human/delegation decision references, incomparable briefs, and exhausted/overrun budgets. It does not authenticate the claimed person or recompute arbitrary filesystem hashes; callers own actual artifact capture and runtime authorization.

The real ledger validates an optional `improvement_round` before append, stores the computed status, and excludes an undone or critically blocked candidate from its score champion. Legacy records remain readable. “Accepted” continues to describe legacy score ranking; the separate status records adoption. It does not grant shipping permission.

When supplied beside a recipe work directory, `improvement_round.json` travels through `dlx.py` into the ledger record. Malformed JSON fails loudly; an absent optional record is not fabricated. Both embedded recipe helpers are synchronized with the canonical `dlx.py`. Reports show the supplied brief/hypothesis, independent taste/elegance reasons, gates, decision source and rollback, and label a passing score bar **Ready for review**. The application payload exposes `review_ready`; historical `ship` is now false rather than inferring authorization from a score.

Fictional keep, undo and exhausted-budget records under `fixtures/improvement-round/` include actual small baseline/candidate HTML and hashes. The tests exercise the canonical JSON Schema, semantic adapter, real ledger append/query/champion path, recipe helper, report escaping and app payload. These are deterministic conformance cases, not observed taste improvement, provider quality, outside use or an effectiveness study.

Rollback: remove the optional round input/adapter and restore the prior display/payload commit together if a consumer needs the historical convention. Preserve every existing ledger and baseline; no data migration or deletion occurs. A release must document the `ship`→`review_ready` semantic change for external consumers before deployment.
