# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Regression tests for LlamaCppBackend._find_free_port.

The fork pins the llama-server port via ``UNSLOTH_LLAMA_SERVER_PORT``.
The pin MUST be validated against the actual socket state: a long-lived
RAG embedder can hold the same port, and a bind-failed spawn can be
masked by the embedder still answering /health.

Without these tests, a busy-port regression would silently fall back to
"the wrong server is healthy, the load succeeded" -- the original
"server keeps dying when I switch or select a model" symptom on the
user's fork.
"""

from __future__ import annotations

import socket
import sys
import types as _types
from pathlib import Path
from unittest import mock

import pytest

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

_loggers_stub = _types.ModuleType("loggers")
_loggers_stub.get_logger = lambda name: __import__("logging").getLogger(name)
sys.modules.setdefault("loggers", _loggers_stub)
sys.modules.setdefault("structlog", _types.ModuleType("structlog"))

from core.inference.llama_cpp import LlamaCppBackend  # noqa: E402


@pytest.fixture(autouse = True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("UNSLOTH_LLAMA_SERVER_PORT", raising = False)


def _capture_warnings(monkeypatch) -> list:
    """Capture module-logger .warning() messages directly -- immune to
    whatever logging/structlog config sibling test modules installed
    (mirrors TestCrashLogTail._capture_error_logs in the wait-for-health
    suite)."""
    import core.inference.llama_cpp as _llama_mod

    records: list = []
    fake_logger = mock.Mock()
    fake_logger.warning = mock.Mock(side_effect = lambda msg, *a, **k: records.append(msg))
    # Stub info/error too so any sibling test that triggers them does
    # not blow up; only warning is asserted on.
    fake_logger.info = mock.Mock()
    fake_logger.error = mock.Mock()
    monkeypatch.setattr(_llama_mod, "logger", fake_logger)
    return records


class TestFindFreePort:
    """``_find_free_port`` honours the env pin only when the port is free."""

    def test_no_env_returns_os_assigned_port(self):
        """Upstream behaviour: no env var means an OS-assigned free port."""
        port = LlamaCppBackend._find_free_port()
        assert 1 <= port <= 65535
        # Sanity: a fresh ephemeral port from bind(0) is in the dynamic range.
        assert port >= 1024

    def test_env_port_free_is_returned(self, monkeypatch):
        """A free env-pinned port is returned verbatim."""
        # Pick a free port by binding(0), then release it. Tiny race window
        # is acceptable for a test (the test machine is otherwise idle).
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        # The socket above is now closed; the port is *likely* free, but
        # on a contended box TIME_WAIT could hold it. Re-check.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", free_port))
            except OSError:
                pytest.skip("port reuse in TIME_WAIT on this host; pick another")
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", str(free_port))
        assert LlamaCppBackend._find_free_port() == free_port

    def test_env_port_busy_falls_back_and_warns(self, monkeypatch):
        """A busy env-pinned port must NOT be returned: log a warning and
        return an OS-assigned free port. This is the regression guard for
        the user's "server keeps dying" symptom -- the embedder was on
        12606, the chat spawn tried to bind 12606, the bind failed, and
        Studio's /health probe falsely confirmed via the embedder."""
        # Hold a port open with a real listener.
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            holder.bind(("127.0.0.1", 0))
            holder.listen(1)
            busy_port = holder.getsockname()[1]
        except OSError:
            holder.close()
            pytest.skip("could not bind a holder socket on this host")
        records = _capture_warnings(monkeypatch)
        try:
            monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", str(busy_port))
            returned = LlamaCppBackend._find_free_port()
            assert returned != busy_port, (
                "busy env port must not be returned; the spawn would "
                "bind-fail and the /health probe would hit the holder"
            )
            # The fallback must be a real, free port we can still bind.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", returned))
            # The warning must mention the busy port so the user can act.
            joined = " ".join(records)
            assert f"UNSLOTH_LLAMA_SERVER_PORT={busy_port}" in joined
            assert "busy" in joined.lower()
        finally:
            holder.close()

    def test_env_port_invalid_value_falls_back(self, monkeypatch):
        """A non-numeric env value must not crash; the OS-assigned branch
        runs instead (preserves the original fallback semantics)."""
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "not-a-port")
        port = LlamaCppBackend._find_free_port()
        assert 1 <= port <= 65535
        assert port >= 1024

    def test_env_port_out_of_range_falls_back(self, monkeypatch):
        """A port outside 1..65535 must not be returned verbatim."""
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "70000")
        port = LlamaCppBackend._find_free_port()
        assert 1 <= port <= 65535

    def test_env_port_zero_falls_back(self, monkeypatch):
        """``UNSLOTH_LLAMA_SERVER_PORT=0`` is a privileged request
        (port 0 means "OS-assigned" in socket APIs) and must not be
        returned as 0 -- the caller would then ask llama-server to bind
        port 0, which the user almost never wants."""
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "0")
        port = LlamaCppBackend._find_free_port()
        assert 1 <= port <= 65535
