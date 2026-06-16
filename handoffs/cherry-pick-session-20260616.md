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

## Candidates 2–4: Studio threads, CLI local-dataset, GGUF variant selection

**Combined branch:** `cherry-pick/unsloth-5894-6357-6342-studio-cli-gguf`
**Integration base:** `feature/pin-llama-server-port`

### Commit 2: Studio threads fix (PR #5894)

**Upstream commit:** `5a38447b2`
**Subject:** `Studio: omit --threads when unset so llama.cpp picks physical cores (#5894)`
**Risk level:** Low
**Files changed:** `studio/backend/core/inference/llama_cpp.py`
**Cherry-pick result:** Required conflict resolution. The feature branch's port-pinning work had changed the same `--threads` block and added redundant `import os, sys` in the library-path section. Resolved by keeping the upstream behavior (omit `--threads` when unset) and removing the redundant imports.

### Commit 3: CLI local-dataset fix (PR #6357)

**Upstream commit:** `0ac1fb5d9`
**Subject:** `CLI: fix --local-dataset being parsed as a string instead of a list (#6357)`
**Risk level:** Low
**Files changed:**
- `studio/backend/core/training/trainer.py`
- `unsloth_cli/commands/studio.py`
**Cherry-pick result:** Clean apply.

### Commit 4: GGUF variant file selection fix (PR #6342)

**Upstream commit:** `048f34e8f`
**Subject:** `Fix GGUF variant file selection (#6342)`
**Risk level:** Medium
**Files changed:** 12 files across `studio/backend/core/inference/`, `studio/backend/hub/`, `studio/backend/routes/`, `studio/backend/utils/`, and `studio/frontend/src/features/chat/api/chat-adapter.ts`.
**Cherry-pick result:** Clean apply.

**Validation commands run:**
```bash
python3 -m py_compile studio/backend/core/inference/llama_cpp.py studio/backend/core/training/trainer.py unsloth_cli/commands/studio.py
python3 -m pytest tests/studio/test_cli_studio_defaults.py tests/studio/test_export_output_path_contract.py -x -q
python3 -m pytest tests/studio/test_llama_cpp_wall_clock_cap.py tests/studio/test_cli_run_alias.py -x -q
```

**Validation results:**
- Syntax check: passed.
- `test_cli_studio_defaults.py` + `test_export_output_path_contract.py`: 8 passed.
- `test_llama_cpp_wall_clock_cap.py` + `test_cli_run_alias.py`: 5 passed.

**Decision:** Keep all three. The low-risk fixes apply cleanly (or with minimal conflict resolution), and the medium-risk GGUF fix passes targeted tests.

**Combined branch pushed to fork:** `jecruz/unsloth:cherry-pick/unsloth-5894-6357-6342-studio-cli-gguf`

---

---

## Branch consolidation: merge three branches into `feature/pin-llama-server-port`

**Action:** Merged the three open cherry-pick/documentation branches into the integration base.

1. `cherry-pick/unsloth-5894-6357-6342-studio-cli-gguf` → fast-forward.
2. `cherry-pick/unsloth-6351-cve-rng-state` → resolved handoff-file conflict.
3. `docs/cherry-pick-policy` → resolved conflicts in:
   - `CHERRY-PICK-POLICY.md` (kept private-fork wording).
   - `studio/backend/run.py` (combined port-pinning + upstream `--secure` flag).
   - `unsloth_cli/commands/studio.py` (combined port-pinning + upstream `--secure` flag).

**Side effect:** `docs/cherry-pick-policy` was based on a newer `origin/main`, so the merge also pulled in upstream changes including the `--secure` Cloudflare tunnel feature and related tool-policy work.

**Validation commands run after merges:**
```bash
python3 -m py_compile studio/backend/run.py unsloth_cli/commands/studio.py studio/backend/core/inference/llama_cpp.py unsloth/import_fixes.py unsloth/_gpu_init.py studio/backend/core/training/trainer.py
python3 -m pytest unsloth_cli/tests/test_studio_cloudflare_flag.py unsloth_cli/tests/test_studio_secure_flag.py -v
python3 -m pytest studio/backend/tests/test_secure_tunnel_gate.py -v
python3 -m pytest tests/studio/test_cli_repo_variant.py studio/backend/tests/test_cached_gguf_routes.py studio/backend/tests/test_offline_gguf_cache_fallback.py -v
```

**Validation results:**
- Syntax check: passed.
- Cloudflare + secure flag tests: 24 passed.
- Secure tunnel gate tests: 15 passed.
- Repo-variant / GGUF cache tests: 105 passed, 2 failed (Hugging Face 404 on `org/repo`; network/test-data issue, not a merge regression).
- Signature inspection: `run_server`, `studio_default`, and `run` all expose both `llama_server_port` and `secure` parameters.

**Decision:** Keep. `feature/pin-llama-server-port` now contains the port-pinning feature, the four cherry-picked upstream fixes, the cherry-pick policy docs, and the upstream `--secure` tunnel feature.

## Follow-ups / blockers

1. **Environment:** `unsloth_zoo` was installed in an isolated temp venv and the CVE-specific test that previously failed (`test_accelerate_patch_wired_into_gpu_init`) now passes. The broader `tests/test_import_fixes_drift.py` suite still fails on Python 3.14 with `torch 2.12.0` due to a `TypeError` in `torch/_inductor/runtime/triton_heuristics.py` (`unsupported operand type(s) for |: '_Noop' and 'type'`). This is a Python 3.14 / torch compatibility issue, not a regression from the CVE fix. Use Python 3.11–3.12 or a newer torch build to run the full drift suite.
2. **Fork main alignment:** `fork/main` and `origin/main` have unrelated histories. Merging upstream into `fork/main` is not safe without further analysis. Consider either:
   - Keeping `feature/pin-llama-server-port` as the active integration base, or
   - Manually reviewing the 3,442 commits unique to `fork/main` before any history rewrite.
3. **Upstream catch-up status:** `origin/main` is currently at `58c2ec1eb` (Xet-primary HTTP fallback). The following planned candidates were already pulled into `feature/pin-llama-server-port` by the `docs/cherry-pick-policy` merge:
   - `58c2ec1eb` Xet-primary HTTP fallback (high risk, now included).
   - `d50a2e2d0` Windows VBS removal (#6326, now included).
   - `f3991ac41` Chat search (#6350, now included).

   Cherry-pick attempts for these commits produced empty trees, confirming they are already present. No further cherry-picks from `origin/main` are available until upstream lands new commits.

4. **Broader validation run:**
   ```bash
   python3 -m pytest unsloth_cli/tests/test_studio_cloudflare_flag.py \
                     unsloth_cli/tests/test_studio_secure_flag.py \
                     tests/studio/test_cli_studio_defaults.py \
                     tests/studio/test_cli_run_alias.py \
                     tests/studio/test_export_output_path_contract.py -q
   python3 -m pytest studio/backend/tests/test_secure_tunnel_gate.py \
                     tests/studio/test_cli_repo_variant.py -q
   python3 -m pytest studio/backend/tests/test_hf_xet_fallback.py -q
   python3 -m pytest tests/studio/install/test_launch_studio_launcher.py -q
   ```
   **Results:** 34 + 36 + 17 + 5 = 92 passed, 1 skipped, 0 failed.

5. **Next options:**
   - Run a full end-to-end Studio smoke test from a proper install (outside this checkout, per the umbrella install/distribution rule).
   - Wait for new upstream commits to land on `origin/main`, then cherry-pick them using the policy.
   - Re-evaluate the `fork/main` unrelated-history problem and decide whether to make `feature/pin-llama-server-port` the effective default branch of the private fork.

6. **Working-tree note:** `README.md` has an uncommitted local-install section that is not part of this cherry-pick work; it was preserved by stashing/popping during branch switches. Do not commit it without explicit user approval.
