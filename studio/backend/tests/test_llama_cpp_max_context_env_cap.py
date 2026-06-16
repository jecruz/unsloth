# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Regression tests for UNSLOTH_LLAMA_SERVER_MAX_CONTEXT env cap."""

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


class TestMaxContextEnvCap:
    """``_apply_max_context_env_cap`` must honor the env var and ignore invalid values."""

    @pytest.fixture(autouse = True)
    def _clean_env(self, monkeypatch):
        monkeypatch.delenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", raising = False)

    def test_caps_explicit_context(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", "4096")
        assert LlamaCppBackend._apply_max_context_env_cap(262144) == 4096

    def test_replaces_zero_with_cap(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", "8192")
        assert LlamaCppBackend._apply_max_context_env_cap(0) == 8192

    def test_leaves_lower_context_unchanged(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", "4096")
        assert LlamaCppBackend._apply_max_context_env_cap(2048) == 2048

    def test_no_env_returns_input(self):
        assert LlamaCppBackend._apply_max_context_env_cap(262144) == 262144

    def test_invalid_env_is_ignored(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", "not_a_number")
        assert LlamaCppBackend._apply_max_context_env_cap(262144) == 262144

    def test_non_positive_env_is_ignored(self, monkeypatch):
        monkeypatch.setenv("UNSLOTH_LLAMA_SERVER_MAX_CONTEXT", "0")
        assert LlamaCppBackend._apply_max_context_env_cap(262144) == 262144
