# Cherry-Pick Session — 2026-06-24 Strategic Merge

**Goal:** Absorb the remaining ~140 upstream commits via a single merge of `origin/main` into our `main`.
**Strategy chosen:** Merge (one conflict pass) — recommended over rebase for this volume.
**Merge commit:** `225d564b9` (merge of `origin/main`)
**Final main:** `2a05d109e` (after auto-compact feature merge)

## Merge stats

- **Upstream commits absorbed:** 182
- **Our commits carried forward:** 66 (all 5 batches + auto-compact + port-pinning)
- **Conflicts:** 21 files
- **Conflict resolution:** 6 simple (took upstream), 15 manual (kept both sides where features diverged)

## Conflicts resolved (21 files)

| File | Resolution |
|------|------------|
| `install.ps1`, `install.sh`, `studio/setup.sh` | Took upstream's more descriptive `--secure` help text |
| `studio/backend/requirements/no-torch-runtime.txt` | Took upstream's more detailed anyio<4.14 comment |
| `studio/backend/requirements/single-env/constraints.txt` | Took upstream's expanded rationale |
| `studio/backend/requirements/single-env/overrides-darwin-arm64.txt` | Took upstream's expanded rationale |
| `studio/backend/tests/test_middleware.py` | Took upstream (added `test_is_pure_asgi_not_basehttp_middleware`) |
| `studio/backend/tests/test_offline_gguf_cache_fallback.py` | Took upstream (added `TestGgufVariantFileResolution`) |
| `studio/backend/tests/test_secure_tunnel_gate.py` | **Kept both** our `test_run_py_accepts_not_secure_flag` and upstream's CORS/secure-env tests |
| `studio/backend/tests/test_torchao_select.py` | Took upstream (added `test_skips_torchao_on_windows_rocm`) |
| `studio/backend/tests/test_validate_model_error.py` | Took upstream (added trust-remote-code tests) |
| `studio/backend/utils/paths/storage_roots.py` | Took upstream (supersets our HF_HOME logic) |
| `studio/install_python_stack.py` | **Kept our** Windows-ROCm `--no-deps` override + took upstream's expanded torchao skip comment |
| `studio/backend/core/inference/llama_cpp.py` | **Kept both** our env-injection helpers + upstream's MTP-crash `_pending_load_kwargs` |
| `studio/backend/core/training/trainer.py` | Took upstream (better error messages, Dataset\|dict signature) |
| `studio/backend/routes/inference.py` | Took upstream (`_maybe_unsupported_message` refactor) |
| `studio/backend/run.py` | **Kept both** our `--llama-server-port`/`--not-secure` + upstream's `--enable-tools`/`--disable-tools` |
| `unsloth_cli/_inference.py` | Took upstream (`urlopen_no_redirect` + IPv4/IPv6 resolution) |
| `unsloth_cli/commands/connect.py` | Took upstream (per-server key bucketing) |
| `unsloth_cli/commands/studio.py` | **Kept both** our `--llama-server-port`/`--not-secure` + upstream's `--enable-tools`/`--disable-tools` |
| `unsloth_cli/tests/test_connect.py` | Took upstream (portable Windows env assertions) |

## Validation

- **199 passed**, 3 skipped, 0 regressions from cherry-picks
- Targeted: test_torchao_select, test_secure_tunnel_gate, test_exec_utf8, test_connect, test_cli_studio_defaults, tests/security/
- Frontend: `tsc -b` clean
- Auto-compact: 8/8 tests pass

## Known regression: `_is_big_endian_gguf_path` filtering

**11 test failures** in `test_offline_gguf_cache_fallback.py::TestGgufVariantFileResolution`:

These tests exercise upstream's `_is_big_endian_gguf_path` filtering (added in PR #6342, commit `6b1a73628`). Our fork **explicitly reverted** this commit (`3bb9cf8b7`, "Revert 'Fix GGUF variant file selection (#6342)'" — author Jeffrey Cruz).

When we merged origin/main, the test file came in cleanly (no conflict) but our reverted implementation was preserved. Result: upstream tests assert behavior that was deliberately removed from our fork.

**Resolution options:**
1. Re-apply PR #6342 (re-introduce `_is_big_endian_gguf_path` filter)
2. Remove the `TestGgufVariantFileResolution` class from the test file
3. Mark these tests `@pytest.mark.xfail(reason="upstream PR #6342 reverted in fork")`

**Recommendation:** Option 3 (xfail) until the original revert rationale is revisited. The revert was a deliberate decision and re-introducing it without understanding why may reintroduce whatever problem it solved.

## Branch state

| Branch | Commit | Notes |
|--------|--------|-------|
| `main` | `2a05d109e` | All cherry-picks + auto-compact + upstream merge |
| `feature/pin-llama-server-port` | `2a05d109e` | Fast-forwarded to main |
| `feature/studio-auto-compact` | `2a05d109e` | Same as main now (merged in) |
