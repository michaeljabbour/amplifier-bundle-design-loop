# Project Context

Phase: web app stabilization. The governed design loop and bodyless bundle
composition already exist; current work adds durable results, run management,
and structured progress. Owner: Michael Jabbour.

The app defaults to DRY mode. Live runs invoke Amplifier as a subprocess scoped
to a run directory. See [run-history.md](../docs/run-history.md) for operation and
acceptance boundaries. No live-provider certification is implied by unit tests.
