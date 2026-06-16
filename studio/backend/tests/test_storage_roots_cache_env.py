# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""Regression tests for the HF cache env setup in utils.paths.storage_roots."""

from pathlib import Path

import pytest

from utils.paths import storage_roots


class TestSetupCacheEnv:
    """_setup_cache_env must respect HF_HOME and derive the hub/xet caches from it."""

    @pytest.fixture(autouse = True)
    def _clean_env(self, monkeypatch):
        """Remove HF cache env vars before each test so the prior test doesn't leak."""
        for key in ("HF_HOME", "HF_HUB_CACHE", "HF_XET_CACHE", "XDG_CACHE_HOME"):
            monkeypatch.delenv(key, raising = False)

    def test_hf_home_derives_hub_and_xet_caches(self, tmp_path, monkeypatch):
        custom_hf = tmp_path / "custom_hf"
        monkeypatch.setenv("HF_HOME", str(custom_hf))

        storage_roots._setup_cache_env()

        assert Path(storage_roots.os.environ["HF_HOME"]).resolve() == custom_hf.resolve()
        assert Path(storage_roots.os.environ["HF_HUB_CACHE"]).resolve() == (custom_hf / "hub").resolve()
        assert Path(storage_roots.os.environ["HF_XET_CACHE"]).resolve() == (custom_hf / "xet").resolve()

    def test_explicit_hf_hub_cache_is_respected(self, tmp_path, monkeypatch):
        custom_hf = tmp_path / "custom_hf"
        explicit_hub = tmp_path / "explicit_hub"
        monkeypatch.setenv("HF_HOME", str(custom_hf))
        monkeypatch.setenv("HF_HUB_CACHE", str(explicit_hub))

        storage_roots._setup_cache_env()

        assert Path(storage_roots.os.environ["HF_HOME"]).resolve() == custom_hf.resolve()
        assert Path(storage_roots.os.environ["HF_HUB_CACHE"]).resolve() == explicit_hub.resolve()
        assert Path(storage_roots.os.environ["HF_XET_CACHE"]).resolve() == (custom_hf / "xet").resolve()

    def test_explicit_hf_xet_cache_is_respected(self, tmp_path, monkeypatch):
        custom_hf = tmp_path / "custom_hf"
        explicit_xet = tmp_path / "explicit_xet"
        monkeypatch.setenv("HF_HOME", str(custom_hf))
        monkeypatch.setenv("HF_XET_CACHE", str(explicit_xet))

        storage_roots._setup_cache_env()

        assert Path(storage_roots.os.environ["HF_HOME"]).resolve() == custom_hf.resolve()
        assert Path(storage_roots.os.environ["HF_HUB_CACHE"]).resolve() == (custom_hf / "hub").resolve()
        assert Path(storage_roots.os.environ["HF_XET_CACHE"]).resolve() == explicit_xet.resolve()

    def test_no_hf_home_uses_default_cache(self, monkeypatch):
        # Force XDG_CACHE_HOME to a known temp path so the default is deterministic.
        tmp_xdg = Path("/tmp")
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_xdg))

        storage_roots._setup_cache_env()

        expected = tmp_xdg / "huggingface"
        assert Path(storage_roots.os.environ["HF_HOME"]).resolve() == expected.resolve()
        assert Path(storage_roots.os.environ["HF_HUB_CACHE"]).resolve() == (expected / "hub").resolve()
        assert Path(storage_roots.os.environ["HF_XET_CACHE"]).resolve() == (expected / "xet").resolve()
