# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Regression tests for UNSLOTH_LLAMA_SERVER_EXTRA_ARGS env injection."""

from __future__ import annotations

import os
import sys
import types as _types
from pathlib import Path

import pytest

_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

_loggers_stub = _types.ModuleType("loggers")
_loggers_stub.get_logger = lambda name: __import__("logging").getLogger(name)
sys.modules.setdefault("loggers", _loggers_stub)

from core.inference.llama_cpp import LlamaCppBackend


class TestExtraArgsEnvInjection:
    """``_apply_extra_args_env_injection`` appends env tokens after Studio's flags."""

    @pytest.fixture(autouse = True)
    def _clean_env(self, monkeypatch):
        monkeypatch.delenv("UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", raising = False)

    def test_no_env_returns_input_unchanged(self):
        assert LlamaCppBackend._apply_extra_args_env_injection(None) is None
        assert LlamaCppBackend._apply_extra_args_env_injection(["-c", "1024"]) == [
            "-c",
            "1024",
        ]

    def test_appends_to_existing_args(self, monkeypatch):
        monkeypatch.setenv(
            "UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "--spec-type off"
        )
        result = LlamaCppBackend._apply_extra_args_env_injection(["-c", "1024"])
        assert result == ["-c", "1024", "--spec-type", "off"]

    def test_appends_when_input_is_none(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "--jinja")
        result = LlamaCppBackend._apply_extra_args_env_injection(None)
        assert result == ["--jinja"]

    def test_managed_flag_is_rejected(self, monkeypatch):
        # -np / --parallel is a managed flag and must not be overridable
        # through the env (would desync app state).
        monkeypatch.setenv(
            "UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "--parallel 4"
        )
        assert LlamaCppBackend._apply_extra_args_env_injection(None) is None

    def test_empty_env_returns_input(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "   ")
        assert LlamaCppBackend._apply_extra_args_env_injection(["-c", "1024"]) == [
            "-c",
            "1024",
        ]

    def test_does_not_mutate_input_list(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "--spec-type off")
        original = ["-c", "1024"]
        LlamaCppBackend._apply_extra_args_env_injection(original)
        assert original == ["-c", "1024"]

    def test_mtp_draft_n_max_workaround_passes_through(self, monkeypatch):
        # Workaround for llama.cpp common/common.cpp:1500-1502: setting
        # n_rs_seq = draft.n_max for MTP causes a 3x RS-buffer inflation
        # that pushes --fit on M3 Max past its budget and drops context
        # to 512. n_max=0 zeros n_rs_seq so MTP still runs at full ctx.
        # --spec-draft-n-max is in _SPEC_FLAGS (strip-on-inherit) but NOT
        # in the validator denylist, so the env value must reach the
        # llama-server command line.
        monkeypatch.setenv(
            "UNSLOTH_LLAMA_SERVER_EXTRA_ARGS", "--spec-draft-n-max 0"
        )
        result = LlamaCppBackend._apply_extra_args_env_injection(
            ["--spec-type", "draft-mtp", "--spec-draft-n-max", "2"]
        )
        assert result == [
            "--spec-type",
            "draft-mtp",
            "--spec-draft-n-max",
            "2",
            "--spec-draft-n-max",
            "0",
        ]
