#!/usr/bin/env python3
"""Regression tests for render.py retry decisions."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render.py"
SPEC = importlib.util.spec_from_file_location("render_entrypoint", SCRIPT)
assert SPEC and SPEC.loader
render_entrypoint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_entrypoint)


def test_should_retry_partial_runtime_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = Path(tmp) / "results.json"
        result.write_text(json.dumps({"summary": {"status": "done", "failed": 1}}), encoding="utf-8")

        retry, reason = render_entrypoint.should_retry_result(result)

        assert retry is True
        assert "1 failed" in reason


def test_should_not_retry_preflight_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = Path(tmp) / "results.json"
        result.write_text(json.dumps({"summary": {"status": "failed_preflight", "failed": 1}}), encoding="utf-8")

        retry, reason = render_entrypoint.should_retry_result(result)

        assert retry is False
        assert "preflight" in reason


if __name__ == "__main__":
    test_should_retry_partial_runtime_failure()
    test_should_not_retry_preflight_failure()
    print("ok")
