"""Run management regressions: isolated data, no provider calls."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from amplifier_module_tool_render_report.history import (
    append_history,
    filter_history,
    read_history,
)
from fastapi.testclient import TestClient

from app import real_runner, storage
from app.dry_runner import _build_dry_state


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DURABLE_ROOT", tmp_path)
    from app import main

    monkeypatch.setattr(main, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(main, "_HISTORY_FILE", tmp_path / "history.jsonl")
    storage.ACTIVE_RUNS.clear()
    with TestClient(main.app) as instance:
        yield instance, main
    storage.ACTIVE_RUNS.clear()


def seed(main, run_id="test-run"):
    root = main.RUNS_DIR / run_id
    root.mkdir(parents=True)
    (root / "meta.json").write_text(
        json.dumps({"kind": "html", "goal": "Keep this goal"})
    )
    (root / "input.html").write_text("<h1>Original</h1>")
    (root / "report.html").write_text("<h1>Report</h1>")
    append_history(main._HISTORY_FILE, json.dumps({"run_id": run_id, "total": 24}))
    return root


@pytest.mark.parametrize(
    "token", ["", ".", "..", "../other", "/tmp/run", "x/y", [], None]
)
def test_run_path_rejects_non_tokens(tmp_path, token):
    assert storage.safe_run_dir(tmp_path, token) is None


def test_run_path_rejects_links_even_to_other_runs(tmp_path):
    (tmp_path / "original").mkdir()
    (tmp_path / "alias").symlink_to(tmp_path / "original")
    assert storage.safe_run_dir(tmp_path, "alias") is None
    assert storage.safe_run_dir(tmp_path, "r-local.1") == tmp_path / "r-local.1"


def test_history_skips_malformed_entries_and_missing_links(client):
    c, main = client
    root = seed(main)
    (root / "report.html").unlink()
    for entry in ["{", "null", "[]", '{"run_id":"../secret"}', '{"run_id":42}']:
        append_history(main._HISTORY_FILE, entry)
    entries = c.get("/api/history").json()["entries"]
    assert len(entries) == 1
    assert entries[0]["goal"] == "Keep this goal"
    assert entries[0]["report_url"] is None


def test_result_reopens_with_canonical_identity_and_existing_artifacts(client):
    c, main = client
    root = seed(main)
    (root / "result.json").write_text(
        json.dumps(
            {"run_id": "wrong", "payload": {"total": 24}, "upgraded_url": "/stale"}
        )
    )
    saved = c.get("/api/run/test-run").json()
    assert saved["type"] == "result"
    assert saved["run_id"] == "test-run"
    assert saved["payload"]["total"] == 24
    assert saved["report_url"] == "/runs/test-run/report.html"
    assert saved["upgraded_url"] is None
    (root / "result.json").write_text("[]")
    assert c.get("/api/run/test-run").json()["payload"] == {}


def test_delete_is_scoped_and_reports_io_failure(client, monkeypatch):
    c, main = client
    target = seed(main)
    other = seed(main, "other")
    storage.ACTIVE_RUNS.add("test-run")
    assert c.delete("/api/run/test-run").status_code == 409
    storage.ACTIVE_RUNS.clear()
    with monkeypatch.context() as m:
        m.setattr(
            main.shutil, "rmtree", lambda path: (_ for _ in ()).throw(PermissionError())
        )
        assert c.delete("/api/run/test-run").status_code == 500
    assert target.exists()
    assert len(c.get("/api/history").json()["entries"]) == 2
    assert c.delete("/api/run/test-run").json()["removed_dir"]
    assert not target.exists() and other.exists()
    assert [e["run_id"] for e in c.get("/api/history").json()["entries"]] == ["other"]
    assert c.post("/api/history/clear").json()["cleared"] == 1
    assert other.exists()


def test_rerun_preserves_previous_results_and_copies_only_inputs(client):
    c, main = client
    previous = seed(main)
    (previous / "gate.json").write_text('{"action":"DONE"}')
    (previous / "result.json").write_text('{"payload":{"total":24}}')
    response = c.post("/api/run/test-run/rerun")
    assert response.status_code == 200
    new = main.RUNS_DIR / response.json()["run_id"]
    assert new != previous
    assert {p.name for p in new.iterdir()} == {"meta.json", "input.html"}
    assert (new / "meta.json").read_text() == (previous / "meta.json").read_text()
    assert (previous / "result.json").exists()


def test_websocket_rejects_traversal_and_persists_completion(client, monkeypatch):
    c, main = client
    from app import ws_handler

    seed(main)
    monkeypatch.setattr(ws_handler, "_is_dry_mode", lambda: True)
    monkeypatch.setattr(
        ws_handler,
        "run_dry",
        AsyncMock(
            return_value={
                "total": 24,
                "reason": "budget_exhausted",
                "converged": False,
                "payload": {"total": 24, "reason_text": "Pass budget exhausted"},
            }
        ),
    )
    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "start", "run_id": "../escaped"})
        assert ws.receive_json()["type"] == "error"
        ws.send_json({"type": "start", "run_id": "test-run"})
        result = ws.receive_json()
        assert result["type"] == "result" and not result["converged"]
        assert result["verdict"] == "Pass budget exhausted"
    assert c.get("/api/run/test-run").json()["payload"] == result["payload"]
    assert not storage.ACTIVE_RUNS


@pytest.mark.parametrize(
    "reason,converged",
    [("bar_met", True), ("budget_exhausted", False), ("plateau", False)],
)
async def test_live_result_uses_gate_reason_and_explicit_bar(
    tmp_path, monkeypatch, reason, converged
):
    from app import audit

    monkeypatch.setattr(
        audit, "run_audit", AsyncMock(return_value={"available": False})
    )
    state = _build_dry_state("live", "escalated")
    files = {
        "gate.json": {"action": "DONE", "reason": reason},
        "best_record.json": state["records"][1],
        "all_records.json": state["records"],
    }
    for name, value in files.items():
        (tmp_path / name).write_text(json.dumps(value))
    (tmp_path / "report.html").write_text("<h1>Report</h1>")
    (tmp_path / "passes.txt").write_text("3")
    result = await real_runner._build_result_from_work_dir(
        "live", tmp_path, kind="prompt", source="brief", options={}, bar=28
    )
    assert result["converged"] is converged
    if reason == "budget_exhausted":
        assert "28/32" in result["payload"]["reason_text"]
        assert "3 passes" in result["payload"]["reason_text"]


async def test_milestones_flush_use_immutable_baseline_and_reject_invalid_scores(
    tmp_path,
):
    baseline = dict.fromkeys(real_runner._DIMS, 1)
    champion = dict.fromkeys(real_runner._DIMS, 3)
    (tmp_path / "pass0").mkdir()
    (tmp_path / "pass0/scores.json").write_text(json.dumps(baseline))
    (tmp_path / "best_scores.json").write_text(json.dumps(champion))
    (tmp_path / "gate.json").write_text('{"action":"DONE","reason":"budget_exhausted"}')
    finished = asyncio.Event()
    hook = AsyncMock()
    task = asyncio.create_task(
        real_runner._watch_milestones(tmp_path, hook, finished, bar=26)
    )
    await asyncio.sleep(0)
    finished.set()
    await asyncio.wait_for(task, 1)
    events = {call.args[0]: call for call in hook.milestone.call_args_list}
    assert events["baseline"].kwargs["total"] == 8
    assert events["decide"].kwargs["total"] == 24
    assert "26/32" in events["decide"].args[1]
    assert real_runner._flat_scores({**champion, "point": 5}) is None
    assert real_runner._near_empty_note({}) == ""


def test_history_edit_does_not_lose_competing_appends(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "history.jsonl"
    append_history(path, "remove")
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = [pool.submit(append_history, path, str(i)) for i in range(30)]
        jobs.append(pool.submit(filter_history, path, lambda line: line != "remove"))
        for job in jobs:
            job.result()
    assert set(read_history(path)) == {str(i) for i in range(30)}


async def test_live_runner_finishes_without_cancellation_masking_result(
    tmp_path, monkeypatch
):
    expected = {
        "total": 24,
        "reason": "budget_exhausted",
        "payload": {"reason_text": "Budget exhausted"},
    }
    build = AsyncMock(return_value=expected)
    monkeypatch.setattr(real_runner, "_build_result_from_work_dir", build)
    monkeypatch.setattr(
        real_runner, "_resolve_amplifier_bin", lambda: "/stub/amplifier"
    )
    monkeypatch.setattr(
        real_runner, "_run_cli", AsyncMock(return_value={"status": "success"})
    )
    result = await real_runner.run_real(
        "test",
        tmp_path,
        AsyncMock(),
        kind="prompt",
        source="brief",
        options={"bar": 28},
    )
    assert result == expected
    assert build.call_args.kwargs["bar"] == 28


def test_preflight_checks_the_cli_used_by_live_runs(client, monkeypatch):
    c, main = client
    monkeypatch.setattr(main, "_dry_mode", lambda: False)
    monkeypatch.setattr(
        real_runner, "_resolve_amplifier_bin", lambda: "/stub/amplifier"
    )
    assert c.get("/api/preflight").json()["real_available"]

    def missing_cli():
        raise RuntimeError("missing")

    monkeypatch.setattr(real_runner, "_resolve_amplifier_bin", missing_cli)
    assert c.get("/api/preflight").json()["mode"] == "live-unavailable"
