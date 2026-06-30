"""tests/test_dlx.py — TDD fail-loud contract for dlx.extract and dlx.normscores.

Run with:
  cd ~/dev/amplifier-bundle-design-loop
  PYTHONPATH=recipes .venv/bin/pytest tests/test_dlx.py -q
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
DLX = str(REPO / "recipes" / "dlx.py")
PY = sys.executable

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]


def run_dlx(*args):
    """Run `python3 recipes/dlx.py <args>`, return (stdout, stderr, returncode)."""
    result = subprocess.run(
        [PY, DLX] + list(args),
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    return result.stdout, result.stderr, result.returncode


def write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return str(p)


def valid_scores():
    return {d: 2 for d in DIMS}


def assert_error_sentinel(out, expected_err_type):
    """Assert stdout contains a valid __dlx_error__ sentinel."""
    try:
        obj = json.loads(out.strip())
    except Exception:
        pytest.fail(f"output is not JSON: {out!r}")
    assert "__dlx_error__" in obj, f"no __dlx_error__ key in {obj!r}"
    assert obj["__dlx_error__"] == expected_err_type, (
        f"expected __dlx_error__={expected_err_type!r} but got {obj['__dlx_error__']!r}"
    )
    assert "detail" in obj, f"missing 'detail' key in {obj!r}"


# ===========================================================================
# normscores — VALID paths (must stay GREEN before and after the fix)
# ===========================================================================


def test_normscores_valid_flat_scores(tmp_path):
    """Valid flat 8-dim scores dict → rc=0, emits valid flat JSON."""
    path = write_json(tmp_path, "scores.json", valid_scores())
    out, err, rc = run_dlx("normscores", path)
    assert rc == 0, f"expected rc=0 but got {rc}; stderr={err!r}"
    flat = json.loads(out)
    assert set(flat.keys()) == set(DIMS), f"wrong dims in output: {flat.keys()}"
    assert all(isinstance(v, int) for v in flat.values()), f"non-int values: {flat}"


def test_normscores_valid_nested_scores(tmp_path):
    """Nested {{scores: {{...}}}} wrapper is unwrapped, then succeeds."""
    nested = {"scores": valid_scores(), "total": 16, "reasons": {}}
    path = write_json(tmp_path, "scores.json", nested)
    out, err, rc = run_dlx("normscores", path)
    assert rc == 0, f"expected rc=0 but got {rc}; stderr={err!r}"
    flat = json.loads(out)
    assert set(flat.keys()) == set(DIMS)


# ===========================================================================
# normscores — FAIL-LOUD (RED before fix, GREEN after)
# ===========================================================================


def test_normscores_missing_dim_fails_loud(tmp_path):
    """Missing one dim → error sentinel on stdout + nonzero exit."""
    scores = valid_scores()
    del scores["clarity"]
    path = write_json(tmp_path, "scores.json", scores)
    out, err, rc = run_dlx("normscores", path)
    assert rc != 0, (
        f"expected nonzero rc for missing dim; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "invalid_scores")


def test_normscores_float_value_fails_loud(tmp_path):
    """Float value (e.g. 2.5) → error sentinel + nonzero exit."""
    scores = valid_scores()
    scores["clarity"] = 2.5
    path = write_json(tmp_path, "scores.json", scores)
    out, err, rc = run_dlx("normscores", path)
    assert rc != 0, (
        f"expected nonzero rc for float value; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "invalid_scores")


def test_normscores_bool_value_fails_loud(tmp_path):
    """Bool value (bool is subclass of int — must be rejected) → error sentinel + nonzero."""
    scores = valid_scores()
    scores["clarity"] = True  # bool, not int
    path = write_json(tmp_path, "scores.json", scores)
    out, err, rc = run_dlx("normscores", path)
    assert rc != 0, (
        f"expected nonzero rc for bool value; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "invalid_scores")


def test_normscores_out_of_range_fails_loud(tmp_path):
    """Value out of 0..4 range (e.g. 5) → error sentinel + nonzero."""
    scores = valid_scores()
    scores["clarity"] = 5
    path = write_json(tmp_path, "scores.json", scores)
    out, err, rc = run_dlx("normscores", path)
    assert rc != 0, (
        f"expected nonzero rc for out-of-range value; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "invalid_scores")


def test_normscores_negative_value_fails_loud(tmp_path):
    """Negative value (e.g. -1) → error sentinel + nonzero."""
    scores = valid_scores()
    scores["elegance"] = -1
    path = write_json(tmp_path, "scores.json", scores)
    out, err, rc = run_dlx("normscores", path)
    assert rc != 0, (
        f"expected nonzero rc for negative value; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "invalid_scores")


# ===========================================================================
# extract — VALID path (must stay GREEN)
# ===========================================================================


def _make_invoke_output(result_value):
    """Simulate `amplifier tool invoke --output json` stdout: log lines + JSON block.

    The real CLI emits result as a JSON string whose value is a Python repr
    (single-quote dict), e.g.  "result": "{\'k\': 1}".  json.dumps(repr(...))
    produces exactly that double-quoted wrapper.
    """
    import json as _json
    return (
        "some log line\n"
        "another log line\n"
        "{\n"
        '  "status": "ok",\n'
        '  "tool": "design_controller",\n'
        f'  "result": {_json.dumps(repr(result_value))}\n'
        "}"
    )


def test_extract_valid_python_repr(tmp_path):
    """Valid Python-repr result dict → rc=0, emits parsed JSON dict."""
    payload = {"decision": "NEW_BEST", "worst": 2, "total": 16, "regression_flags": []}
    f = tmp_path / "raw.txt"
    f.write_text(_make_invoke_output(payload))
    out, err, rc = run_dlx("extract", str(f))
    assert rc == 0, f"expected rc=0 but got {rc}; stderr={err!r}"
    result = json.loads(out)
    assert result == payload


def test_extract_valid_dict_already_in_json(tmp_path):
    """result is already a JSON dict (not a repr string) → rc=0, emits it."""
    raw = (
        'log line\n'
        '{"status": "ok", "tool": "x", "result": {"foo": "bar"}}'
    )
    f = tmp_path / "raw.txt"
    f.write_text(raw)
    out, err, rc = run_dlx("extract", str(f))
    assert rc == 0, f"expected rc=0 but got {rc}; stderr={err!r}"
    result = json.loads(out)
    assert result == {"foo": "bar"}


# ===========================================================================
# extract — FAIL-LOUD (RED before fix, GREEN after)
# ===========================================================================


def test_extract_no_status_block_fails_loud(tmp_path):
    """No {{\"status\"...}} block in output → error sentinel on stdout + nonzero."""
    f = tmp_path / "raw.txt"
    f.write_text("some garbage output\nno json status block here\n")
    out, err, rc = run_dlx("extract", str(f))
    assert rc != 0, (
        f"expected nonzero rc for missing status block; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "extract_failed")


def test_extract_empty_file_fails_loud(tmp_path):
    """Empty file (tool invoke failed silently) → error sentinel + nonzero."""
    f = tmp_path / "raw.txt"
    f.write_text("")
    out, err, rc = run_dlx("extract", str(f))
    assert rc != 0, (
        f"expected nonzero rc for empty file; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "extract_failed")


def test_extract_garbage_repr_fails_loud(tmp_path):
    """Status block present but result string is unparseable Python repr → error sentinel + nonzero."""
    # result is a string that looks like it should be a Python repr but isn't valid
    raw = '{"status": "ok", "tool": "foo", "result": "{{not valid python: [}}"}'
    f = tmp_path / "raw.txt"
    f.write_text(raw)
    out, err, rc = run_dlx("extract", str(f))
    assert rc != 0, (
        f"expected nonzero rc for unparseable repr; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "extract_failed")


def test_extract_nonexistent_file_fails_loud(tmp_path):
    """Nonexistent file → error sentinel + nonzero (not crash)."""
    bad_path = str(tmp_path / "does_not_exist.txt")
    out, err, rc = run_dlx("extract", bad_path)
    assert rc != 0, (
        f"expected nonzero rc for missing file; got rc={rc}\nout={out!r}"
    )
    assert_error_sentinel(out, "extract_failed")


# ===========================================================================
# classify_input — RED (all fail until classify_input + classify subcommand added)
# ===========================================================================


def _ci(s: str) -> str:
    """Direct Python import of classify_input (no subprocess)."""
    import importlib, sys
    sys.path.insert(0, str(REPO / "recipes"))
    import dlx as _dlx
    # Force reload so we always get the latest version
    importlib.reload(_dlx)
    return _dlx.classify_input(s)


class TestClassifyInput:
    def test_url_http(self):
        assert _ci("http://example.com") == "url"

    def test_url_https(self):
        assert _ci("https://example.com/page") == "url"

    def test_url_with_html_suffix(self):
        """A URL that ends in .html is still 'url' — URL check wins."""
        assert _ci("https://example.com/about.html") == "url"

    def test_url_with_png_suffix(self):
        """A URL that ends in .png is 'url', not 'image' — URL check is first."""
        assert _ci("https://cdn.example.com/hero.png") == "url"

    def test_html_extension(self):
        assert _ci("mypage.html") == "html"

    def test_htm_extension(self):
        assert _ci("mypage.htm") == "html"

    def test_html_relative_path(self):
        """Relative path with .html extension."""
        assert _ci("./fixtures/slop.html") == "html"

    def test_html_absolute_existing(self):
        """Absolute path that actually exists on disk with .html ext."""
        p = str(REPO / "fixtures" / "slop.html")
        assert _ci(p) == "html"

    def test_html_uppercase_extension(self):
        """Case-insensitive: .HTML -> html."""
        assert _ci("page.HTML") == "html"

    def test_image_png(self):
        assert _ci("screenshot.png") == "image"

    def test_image_jpg(self):
        assert _ci("photo.jpg") == "image"

    def test_image_jpeg(self):
        assert _ci("photo.jpeg") == "image"

    def test_image_webp(self):
        assert _ci("design.webp") == "image"

    def test_image_gif(self):
        assert _ci("anim.gif") == "image"

    def test_image_uppercase_extension(self):
        """Case-insensitive: .PNG -> image."""
        assert _ci("shot.PNG") == "image"

    def test_prompt_bare_prose(self):
        assert _ci("Make a landing page for my SaaS startup") == "prompt"

    def test_prompt_short(self):
        assert _ci("pricing page redesign") == "prompt"

    def test_prompt_path_no_extension(self):
        """A bare path without a recognized extension -> prompt."""
        assert _ci("/tmp/myfile") == "prompt"

    def test_prompt_empty(self):
        """Edge: empty string -> prompt (no recognizable kind)."""
        assert _ci("") == "prompt"


class TestClassifySubcommand:
    def test_classify_url(self):
        out, err, rc = run_dlx("classify", "https://example.com")
        assert rc == 0, f"rc={rc} stderr={err!r}"
        obj = json.loads(out)
        assert obj == {"kind": "url"}

    def test_classify_html(self):
        out, err, rc = run_dlx("classify", "page.html")
        assert rc == 0, f"rc={rc} stderr={err!r}"
        assert json.loads(out) == {"kind": "html"}

    def test_classify_image(self):
        out, err, rc = run_dlx("classify", "photo.png")
        assert rc == 0, f"rc={rc} stderr={err!r}"
        assert json.loads(out) == {"kind": "image"}

    def test_classify_prompt(self):
        out, err, rc = run_dlx("classify", "redesign my homepage")
        assert rc == 0, f"rc={rc} stderr={err!r}"
        assert json.loads(out) == {"kind": "prompt"}


# ===========================================================================
# designspec — RED (fails until designspec command added)
# ===========================================================================

DIMS = [
    "clarity", "elegance", "restraint", "empowerment",
    "agency", "ease", "character", "point",
]


def _make_run_dir(tmp_path: Path) -> Path:
    """Create a minimal run dir with all_records.json and best_record.json."""
    scores_a = {d: 1 for d in DIMS}
    scores_b = {d: 2 for d in DIMS}
    records = [
        {
            "run_id": "r-test", "task_class": "lp", "pass": 0, "signature": "s",
            "rubric_version": "v1", "outcome": "accepted", "scores": scores_a,
            "fix_batch": [], "decision": "NEW_BEST", "entry_id": 0,
        },
        {
            "run_id": "r-test", "task_class": "lp", "pass": 1, "signature": "s",
            "rubric_version": "v1", "outcome": "accepted", "scores": scores_b,
            "fix_batch": ["reduced Inter font usage", "removed purple gradient"],
            "decision": "NEW_BEST", "entry_id": 1,
        },
    ]
    best = records[-1]
    (tmp_path / "all_records.json").write_text(json.dumps(records))
    (tmp_path / "best_record.json").write_text(json.dumps(best))
    return tmp_path


class TestDesignspec:
    def test_designspec_writes_file(self, tmp_path):
        """designspec writes design-spec.txt to the run dir."""
        d = _make_run_dir(tmp_path)
        out, err, rc = run_dlx("designspec", str(d))
        assert rc == 0, f"rc={rc} stderr={err!r}\nout={out!r}"
        spec_path = d / "design-spec.txt"
        assert spec_path.exists(), "design-spec.txt was not created"
        content = spec_path.read_text()
        assert len(content) > 0, "design-spec.txt is empty"

    def test_designspec_contains_total(self, tmp_path):
        """design-spec.txt mentions champion total score."""
        d = _make_run_dir(tmp_path)
        run_dlx("designspec", str(d))
        content = (d / "design-spec.txt").read_text()
        # scores_b = {d: 2 for d in DIMS}, total = 16
        assert "16" in content, f"Champion total '16' not found in spec:\n{content}"

    def test_designspec_contains_dims(self, tmp_path):
        """design-spec.txt includes dimension scores."""
        d = _make_run_dir(tmp_path)
        run_dlx("designspec", str(d))
        content = (d / "design-spec.txt").read_text()
        for dim in DIMS:
            assert dim in content, f"Dim '{dim}' not found in spec"

    def test_designspec_contains_accepted_fixes(self, tmp_path):
        """design-spec.txt lists accepted fix items from pass > 0."""
        d = _make_run_dir(tmp_path)
        run_dlx("designspec", str(d))
        content = (d / "design-spec.txt").read_text()
        assert "Inter" in content or "gradient" in content or "reduced" in content, (
            f"Accepted fixes not found in spec:\n{content}"
        )

    def test_designspec_returns_json(self, tmp_path):
        """stdout is valid JSON with 'spec' and 'spec_path' keys."""
        d = _make_run_dir(tmp_path)
        out, err, rc = run_dlx("designspec", str(d))
        assert rc == 0, f"rc={rc} stderr={err!r}"
        obj = json.loads(out)
        assert "spec" in obj, f"'spec' key missing: {obj}"
        assert "spec_path" in obj, f"'spec_path' key missing: {obj}"
        assert str(d) in obj["spec_path"], "spec_path should be under run dir"

    def test_designspec_deterministic(self, tmp_path):
        """Running designspec twice on same dir produces identical output."""
        d = _make_run_dir(tmp_path)
        out1, _, _ = run_dlx("designspec", str(d))
        out2, _, _ = run_dlx("designspec", str(d))
        assert out1 == out2, "designspec output is not deterministic"

    def test_designspec_empty_records(self, tmp_path):
        """Works gracefully when all_records.json is empty list."""
        (tmp_path / "all_records.json").write_text("[]")
        (tmp_path / "best_record.json").write_text("{}")
        out, err, rc = run_dlx("designspec", str(tmp_path))
        assert rc == 0, f"rc={rc} stderr={err!r}"
        assert (tmp_path / "design-spec.txt").exists()


def test_default_durable_base_is_downloads(monkeypatch):
    import dlx
    from pathlib import Path
    monkeypatch.delenv("DESIGN_LOOP_HOME", raising=False)
    base = Path(dlx._default_durable_base())
    assert base.name == "design-loop"
    assert base.parent.name == "Downloads"
    assert base.parent.parent == Path.home()


def test_default_durable_base_env_override(monkeypatch, tmp_path):
    import dlx
    monkeypatch.setenv("DESIGN_LOOP_HOME", str(tmp_path / "custom"))
    assert dlx._default_durable_base() == str(tmp_path / "custom")
