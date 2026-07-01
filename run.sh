#!/usr/bin/env bash
# Run the Design Loop web app.
#
# Dependencies (fastapi, uvicorn[standard], python-multipart) are already
# installed into this repo's existing .venv -- see app/pyproject.toml for
# the exact command used and why `uv sync` isn't used here (the repo root
# pyproject.toml is a deliberate no-op editable package hosting pytest
# config for modules/*, not a real dependency set to resolve against).
#
# DESIGN_LOOP_DRY defaults to 1 (scripted, zero-cost transcript). Set it to
# 0 only once you have installed amplifier_foundation (see app/real_runner.py
# for the exact install command) and are ready to spend real LLM tokens on
# an actual design-converge.yaml run.
set -euo pipefail
cd "$(dirname "$0")"

export DESIGN_LOOP_DRY="${DESIGN_LOOP_DRY:-1}"
PORT="${PORT:-8010}"

echo "Starting Design Loop web app on http://localhost:${PORT} (DESIGN_LOOP_DRY=${DESIGN_LOOP_DRY})"
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
