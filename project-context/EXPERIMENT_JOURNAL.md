# Verification journal

2026-09-11: isolated Python 3.12 environment, temporary run storage, deterministic
suite and Chromium DRY acceptance. The initial suite lacked Foundation; installing
the required offline-composition dependency resolved those two setup failures.
A browser assertion initially checked the old Results DOM before a re-run began;
waiting for Working resolved the test race. Mobile inspection found navigation
overflow, fixed with a two-row layout. Live model quality/cost remains untested.
