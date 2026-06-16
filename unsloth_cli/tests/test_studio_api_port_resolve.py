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
     port and warn (via the optional ``warn`` callback; default writes
     to stderr through ``typer.echo``).
"""

from __future__ import annotations

import inspect
import os
import socket
import subprocess
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


class _ExecSentinel(Exception):
    """Raised by the mocked os.execvp to short-circuit the re-exec path."""


def _capture_execvp(monkeypatch, studio_mod):
    """Replace os.execvp with a recorder that raises _ExecSentinel.

    Returns the capture list; the captured args are appended on call.
    """
    captured: list[list[str]] = []

    def fake_execvp(file, args):
        captured.append(list(args))
        raise _ExecSentinel()

    monkeypatch.setattr(os, "execvp", fake_execvp)
    # Also patch the symbol the function actually uses (it's imported as
    # ``os.execvp`` in the module, so the monkeypatch above is enough).
    return captured


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

    def test_explicit_zero_treated_as_set(self):
        """0 is a valid port (kernel assigns ephemeral) but the resolver
        passes through whatever the CLI gave, even 0, so the user can
        opt into OS-assigned explicitly."""
        studio_mod = _load_studio_mod()
        assert studio_mod._resolve_studio_api_port(0) == 0

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
        """8888 in use (no SO_REUSEADDR) -> function returns a non-8888 port
        and emits a warning to the warn callback."""
        studio_mod = _load_studio_mod()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 8888))
        except OSError:
            pytest.skip("8888 not free on this host")
        try:
            warnings: list[str] = []
            port = studio_mod._resolve_studio_api_port(None, warn = warnings.append)
            assert port != 8888, "should have fallen back from busy 8888"
            assert 1024 <= port <= 65535
            assert len(warnings) == 1, "exactly one warning expected on fallback"
            assert "8888" in warnings[0]
            assert "in use" in warnings[0]
        finally:
            s.close()

    def test_preferred_busy_falls_back_to_ephemeral(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        studio_mod = _load_studio_mod()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 12607))
        except OSError:
            pytest.skip("12607 not free on this host")
        try:
            warnings: list[str] = []
            port = studio_mod._resolve_studio_api_port(None, warn = warnings.append)
            assert port != 12607, "should have fallen back from busy 12607"
            assert 1024 <= port <= 65535
            assert len(warnings) == 1
            assert "12607" in warnings[0]
        finally:
            s.close()

    def test_no_warning_on_clean_path(self, monkeypatch):
        """Sanity: when the preferred port is free, no warning fires."""
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        studio_mod = _load_studio_mod()
        warnings: list[str] = []
        port = studio_mod._resolve_studio_api_port(None, warn = warnings.append)
        assert port == 12607
        assert warnings == []

    def test_fallback_writes_to_stderr_when_warn_not_provided(
        self, monkeypatch, capsys
    ):
        """Production path: when the caller does not pass ``warn`` (CLI
        default), the busy-port message goes to stderr via typer.echo.
        Mirrors the smoke-test contract a real user would see.
        """
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 12607))
        except OSError:
            pytest.skip("12607 not free on this host")
        try:
            studio_mod = _load_studio_mod()
            port = studio_mod._resolve_studio_api_port(None)
            assert port != 12607
            captured = capsys.readouterr()
            assert "12607" in captured.err
            assert "in use" in captured.err
            assert captured.out == ""  # warning is stderr-only
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

        sig = inspect.signature(studio_mod.run)
        opt = sig.parameters["port"].default
        # typer.OptionInfo: ``default`` is None when no default was set.
        assert getattr(opt, "default", "missing") is None

    def test_run_port_option_help_mentions_env_var(self):
        studio_mod = _load_studio_mod()

        sig = inspect.signature(studio_mod.run)
        opt = sig.parameters["port"].default
        help_text = getattr(opt, "help", "") or ""
        assert "UNSLOTH_LLAMA_SERVER_PORT" in help_text
        assert "8888" in help_text

    def test_studio_default_port_option_is_optional(self):
        """Same contract on the ``unsloth studio`` parent command."""
        studio_mod = _load_studio_mod()

        sig = inspect.signature(studio_mod.studio_default)
        opt = sig.parameters["port"].default
        assert getattr(opt, "default", "missing") is None


class TestCliRunnerIntegration:
    """End-to-end through typer's CliRunner.

    Verifies the full argv path: the user types ``unsloth studio run
    --model X`` (no ``--port``), the env var is set, the resolver picks
    the neighbour, and that resolved value reaches ``load_model_via_http``
    (i.e. is forwarded, not re-defaulted to 8888).
    """

    def test_run_help_no_port_shows_env_aware_default(self, monkeypatch):
        """The --help output should describe the env-aware default,
        not a hard 8888, so users know about the rule.

        Note: typer truncates long tokens to fit its column, so we
        assert on the truncated 'UNSLOTH_LLAMA_S…' (the visible form
        when --port's help text wraps in the Options panel) along with
        the words that survive the column clip: '8888', 'ephemeral',
        and the prose 'when set'.
        """
        studio_mod = _load_studio_mod()
        from unsloth_cli import app
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["studio", "run", "--help"],
            env = {"UNSLOTH_LLAMA_SERVER_PORT": "12606"},
        )
        assert result.exit_code == 0
        # Truncated token (column clip in the Options panel) and prose.
        assert "UNSLOTH_LLAMA_S" in result.output, (
            f"env var name not in --help output; got:\n{result.output[-800:]}"
        )
        assert "8888" in result.output
        assert "ephemeral" in result.output
        assert "when set" in result.output

    def test_resolved_port_is_forwarded_to_execvp(self, monkeypatch, tmp_path):
        """When the resolver picks a port, that exact value must reach
        the re-exec target (not 8888). We stub os.execvp (the macOS /
        Linux re-exec path) to capture the args list and short-circuit
        the actual process replace.

        The re-exec path only runs when *out* of the studio venv; we
        set up a fake venv directory with a ``bin/unsloth`` shim so the
        "studio venv missing entry point" gate passes, and patch
        ``sys.prefix`` to force the out-of-venv branch.
        """
        studio_mod = _load_studio_mod()
        captured = _capture_execvp(monkeypatch, studio_mod)

        # Lay down a fake venv: bin/python + bin/unsloth (both files).
        fake_venv = tmp_path / "fake-venv"
        fake_bin = fake_venv / "bin"
        fake_bin.mkdir(parents = True)
        (fake_bin / "python").write_text("#!/bin/sh\nexit 0\n")
        (fake_bin / "unsloth").write_text("#!/bin/sh\nexit 0\n")

        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_PORT", "12606")
        monkeypatch.setattr(studio_mod, "_studio_venv_python", lambda: fake_bin / "python")
        # sys.prefix.startswith(studio_venv_dir) is True in this test
        # environment; force the out-of-venv branch.
        monkeypatch.setattr(studio_mod.sys, "prefix", str(fake_venv))

        from unsloth_cli import app
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "studio",
                "run",
                "--model",
                "unsloth/Qwen3.6-27B-MTP-GGUF",
                "--gguf-variant",
                "UD-Q4_K_XL",
                "--max-seq-length",
                "4096",
            ],
        )
        if not captured:
            pytest.fail(
                f"os.execvp was not called. typer exit={result.exit_code}, "
                f"output:\n{result.output}\nexception: {result.exception!r}"
            )
        args = captured[0]
        assert "--port" in args, f"--port missing from re-exec args: {args}"
        port_idx = args.index("--port")
        assert args[port_idx + 1] == "12607", (
            f"expected --port 12607 (UNSLOTH_LLAMA_SERVER_PORT+1), "
            f"got {args[port_idx + 1]!r} in {args}"
        )
