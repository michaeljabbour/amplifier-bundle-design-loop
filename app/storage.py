"""Shared artifact location and run-directory validation for HTTP and WebSocket."""

import os
import re
from pathlib import Path

DURABLE_ROOT = (
    Path(
        os.environ.get(
            "DESIGN_LOOP_DATA_DIR", str(Path.home() / "Downloads" / "design-loop")
        )
    )
    .expanduser()
    .resolve()
)


def safe_run_dir(runs_dir: Path, run_id: str) -> Path | None:
    """Accept a single run token, never the root or a symlink to another run."""
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id
    ):
        return None
    root = runs_dir.resolve()
    candidate = root / run_id
    if candidate.is_symlink() or candidate.resolve().parent != root:
        return None
    return candidate


# The app runs one worker. Reserve before scheduling a task so two sockets
# cannot write the same run, and deletion cannot race an active runner.
ACTIVE_RUNS: set[str] = set()
