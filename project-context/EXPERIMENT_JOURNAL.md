# Verification journal

2026-09-11: isolated Python 3.12 environment, temporary run storage, deterministic
suite and Chromium DRY acceptance. The initial suite lacked Foundation; installing
the required offline-composition dependency resolved those two setup failures.
A browser assertion initially checked the old Results DOM before a re-run began;
waiting for Working resolved the test race. Mobile inspection found navigation
overflow, fixed with a two-row layout. Live model quality/cost remains untested.

2026-09-24: footprint (chars/4, `scripts/measure_footprint.py`). Own components
11.5k chars (~2.9k tok) -> 5.4k chars (~1.35k tok): tools ~1.93k -> ~0.98k tok,
agents ~640 (~1.16k with examples) -> ~220 tok, context ~310 -> ~145 tok. The dropped
design-intelligence include was ~1.0k tok stripped (~2.1k raw) when the base lacked it.
Mount import: playwright (~0.1-0.2 s) no longer loaded at mount.
