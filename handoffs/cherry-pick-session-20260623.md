# Cherry-Pick Session — 2026-06-23

**Goal:** Batch 1 of upstream fixes onto `feature/pin-llama-server-port`.

**Integration base:** `feature/pin-llama-server-port` (synced with `main` at `e591faf55`)
**Branch:** `cherry-pick/unsloth-batch1-security-training-fixes`

## Candidates

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `61eef657e` (#6599) | Harden MLX self-heal install against supply-chain code execution | Low | **Skipped** — files deleted in our branch (reverted in `3bb9cf8b7`) |
| 2 | `07c7f9bfc` (#6359) | Package scanners: close fail-open gaps in sdist fallback | Low | **Clean** (minor test conflicts resolved) |
| 3 | `b91cdc879` (#6524) | Fix Qwen3 NaN loss: delegate pad_token repair to unsloth_zoo | Low | **Clean** |
| 4 | `a963ec92e` (#6522) | Fix CPOTrainer crash with multimodal processors (Gemma 4) | Low | **Clean** |
| 5 | `9780cdcca` (#6526) | Fix FlashAttention fp32 crash with DoRA (use_dora=True) | Low | **Clean** |
| 6 | `f74c48eb5` (#6523) | Fix GRPOTrainer evaluate() crash without prior training | Low | **Clean** |
| 7 | `eae59b25b` (#6482) | Use EMPTY_LOGITS on fused-CE not-return_dict path | Low | **Clean** |
| 8 | `1b697ed6f` (#6417) | Fix _kill_process AttributeError when _stats_logger is unset | Low | **Clean** (minor llama_cpp.py finally block conflict) |
| 9 | `7fecce4e4` (#6431) | Studio: cross-session backstop to reap leftover llama-server on startup | Low | **Clean** |
| 10 | `8e0d082c9` (#6425) | Reap Studio child processes when parent dies abnormally | Low | **Clean** (kept both UNSLOTH_LLAMA_SERVER_PORT and initialize_parent_lifetime) |

## Conflict resolutions

1. **`tests/security/test_scan_npm_packages.py`** — upstream changed `aws-sdk/metadata.js` to `package/metadata.js`. Accepted upstream.
2. **`tests/security/test_scan_packages.py`** — upstream dropped second `None` arg from `_requires_dist_names` and added `assert "payload>=1"`. Accepted upstream.
3. **`studio/backend/core/inference/llama_cpp.py`** (#6417) — upstream added `_stats_logger.stop()` guard in empty `finally` block. Accepted upstream.
4. **`studio/backend/run.py`** (#6425) — kept both `UNSLOTH_LLAMA_SERVER_PORT` env var and `initialize_parent_lifetime()` call (sequential, no conflict).

## Validation results

| Suite | Result |
|-------|--------|
| Syntax check (6 modified files) | Passed |
| `tests/security/` (87 tests) | **87/87 passed** |
| `test_process_lifetime.py` (16 tests, new from #6425) | **13 passed, 3 skipped** |
| CLI defaults + export tests (8 tests) | **8/8 passed** |
| Studio suite (excluding install/) | 13 passed, 1 pre-existing concurrency-timing failure (unrelated) |

**Decision:** Keep. All 9 applied commits are clean, validated, low-risk.

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-batch1-security-training-fixes`
