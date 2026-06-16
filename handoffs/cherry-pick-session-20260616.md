# Cherry-Pick Session — 2026-06-16

**Goal:** Begin applying the fork's cherry-pick policy to pull upstream changes from `unslothai/unsloth` into our private fork.

**Integration base:** `feature/pin-llama-server-port` (used because `fork/main` has unrelated history with `origin/main` and lacks `unsloth/_gpu_init.py`).

---

## Candidate 1: CVE-2026-1839 fix (PR #6351)

**Upstream commit:** `e046fceb7`
**Subject:** `Harden Trainer._load_rng_state against malicious checkpoints (CVE-2026-1839) (#6351)`
**Risk level:** Low
**Files changed:**
- `unsloth/_gpu_init.py` (+2 lines)
- `unsloth/import_fixes.py` (+69 lines)

**Branch:** `cherry-pick/unsloth-6351-cve-rng-state`
**Cherry-pick result:** Clean apply onto `feature/pin-llama-server-port`.

**Validation commands run:**
```bash
python3 -m py_compile unsloth/_gpu_init.py unsloth/import_fixes.py
python3 -m pytest tests/python/test_gpu_init_ldconfig_guard.py tests/test_import_fixes_drift.py -x -q
```

**Validation results:**
- Syntax check: passed.
- Targeted pytest: 18 passed, 9 skipped, 1 failed.
- Failure: `test_accelerate_patch_wired_into_gpu_init` failed due to missing `unsloth_zoo` dependency in the local environment, not due to the cherry-picked code.

**Decision:** Keep. The security fix is low-risk, applies cleanly, and the only test failure is an environment dependency issue.

**Branch pushed to fork:** `jecruz/unsloth:cherry-pick/unsloth-6351-cve-rng-state`

---

## Follow-ups / blockers

1. **Environment:** Install `unsloth_zoo` and re-run the full test slice for `unsloth/_gpu_init.py` and `unsloth/import_fixes.py` to confirm no regressions.
2. **Fork main alignment:** `fork/main` and `origin/main` have unrelated histories. Merging upstream into `fork/main` is not safe without further analysis. Consider either:
   - Keeping `feature/pin-llama-server-port` as the active integration base, or
   - Manually reviewing the 3,442 commits unique to `fork/main` before any history rewrite.
3. **Next candidates:**
   - `5a38447b2` Studio: omit `--threads` when unset so llama.cpp picks physical cores.
   - `0ac1fb5d9` CLI: fix `--local-dataset` being parsed as a string instead of a list.
   - `048f34e8f` Fix GGUF variant file selection (medium risk, 12 files).
   - `58c2ec1eb` Studio: Xet-primary model downloads with HTTP fallback (high risk, defer until later).
