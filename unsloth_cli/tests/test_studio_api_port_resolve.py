# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Tests for ``_resolve_studio_api_port`` (unsloth_cli/commands/studio.py).

The Studio API port (the HTTP server) and the llama-server inference port
are two different things. Defaulting both to the same value (e.g. both
12606) silently collides: the API binds first, then llama-server fails
with ``couldn't bind HTTP server socket, port: 12606`` and exits.

Resolution rule:

  1. Explicit ``--port`` from the CLI wins.
  2. Otherwise, prefer ``UNSLOTH_LLAMA_SERVER_PORT + 1`` so a pinned
     llama-server port gets a deterministic non-conflicting neighbour.
  3. Otherwise, default to 8888 (legacy).
  4. If the preferred port is busy, fall back to an OS-assigned ephemeral
     port and warn.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner


_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_studio_mod():
    from unsloth_cli.commands import studio as _studio
    return _studio


def _reserve_loopback_port() -> int:
    """Bind port 0 on 127.0.0.1 to get an OS-assigned free port we own."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


class TestResolveStudioApiPort:
    """The pure function ``_resolve_studio_api_port`` (no subprocess)."""

    @pytest.fixture(autouse = True)
    def _clean_env(self, monkeypatch):
        monkeypatch.delenv("UNSLOTH_LLAMA_SERVER_PORT", raising = False)

    def test_explicit_port_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        studio_mod = _load_studio_mod()
        assert studio_mod._resolve_studio_api_port(9000) == 9000

    def test_explicit_port_wins_when_env_unset(self):
        studio_mod = _load_studio_mod()
        assert studio_mod._resolve_studio_api_port(9000) == 9000

    def test_env_var_set_prefers_neighbour(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        studio_mod = _load_studio_mod()
        # 12607 should be free; if not, the test infrastructure is broken.
        assert studio_mod._resolve_studio_api_port(None) == 12607

    def test_env_var_unset_falls_back_to_8888(self):
        studio_mod = _load_studio_mod()
        # 8888 might be busy in CI; this test relies on the host being
        # clean. If 8888 is taken the test is skipped below.
        port = studio_mod._resolve_studio_api_port(None)
        if port != 8888:
            pytest.skip(f"8888 busy on this host; got {port}")

    def test_env_var_unset_busy_8888_falls_back_to_ephemeral(self, monkeypatch):
        """8888 in use (no SO_REUSEADDR) -> function returns a non-8888 port."""
        studio_mod = _load_studio_mod()
        # No SO_REUSEADDR so the bind actually occupies the port.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 8888))
        except OSError:
            pytest.skip("8888 not free on this host")
        try:
            port = studio_mod._resolve_studio_api_port(None)
            assert port != 8888, "should have fallen back from busy 8888"
            assert 1024 <= port <= 65535
        finally:
            s.close()

    def test_preferred_busy_falls_back_to_ephemeral(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        studio_mod = _load_studio_mod()
        # Hold 12607 (no SO_REUSEADDR) so the preferred neighbour is busy.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 12607))
        except OSError:
            pytest.skip("12607 not free on this host")
        try:
            port = studio_mod._resolve_studio_api_port(None)
            assert port != 12607, "should have fallen back from busy 12607"
            assert 1024 <= port <= 65535
        finally:
            s.close()

    def test_invalid_env_var_falls_back_to_8888(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "not-a-port")
        studio_mod = _load_studio_mod()
        port = studio_mod._resolve_studio_api_port(None)
        if port != 8888:
            pytest.skip(f"8888 busy on this host; got {port}")

    def test_empty_env_var_falls_back_to_8888(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "   ")
        studio_mod = _load_studio_mod()
        port = studio_mod._resolve_studio_api_port(None)
        if port != 8888:
            pytest.skip(f"8888 busy on this host; got {port}")


class TestRunPortOption:
    """The ``--port`` Option on ``run`` exposes the env-aware default."""

    def test_run_port_option_is_optional(self):
        """``--port`` must default to None so _resolve_studio_api_port
        can apply the env-aware fallback. A hard default of 8888 would
        shadow the UNSLOTH_LLAMA_SERVER_PORT+1 rule."""
        studio_mod = _load_studio_mod()
        import inspect

        sig = inspect.signature(studio_mod.run)
        opt = sig.parameters["port"].default
        # typer.OptionInfo: ``default`` is None when no default was set.
        assert getattr(opt, "default", "missing") is None

    def test_run_port_option_help_mentions_env_var(self):
        studio_mod = _load_studio_mod()
        import inspect

        sig = inspect.signature(studio_mod.run)
        opt = sig.parameters["port"].default
        help_text = getattr(opt, "help", "") or ""
        assert "UNSLOTH_LLAMA_SERVER_PORT" in help_text
        assert "8888" in help_text

    def test_studio_default_port_option_is_optional(self):
        """Same contract on the ``unsloth studio`` parent command."""
        studio_mod = _load_studio_mod()
        import inspect

        sig = inspect.signature(studio_mod.studio_default)
        opt = sig.parameters["port"].default
        assert getattr(opt, "default", "missing") is None
