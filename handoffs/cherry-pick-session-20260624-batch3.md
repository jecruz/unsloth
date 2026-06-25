# Cherry-Pick Session — 2026-06-24 Batch 3

**Goal:** Low-risk Studio reliability/UX fixes from `origin/main`.
**Integration base:** `main` (at `3e7f59f57`, after Batch 2b merge)
**Branch:** `cherry-pick/unsloth-batch3-studio-reliability-ux`

## Applied

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `f10e47fc5` (#6546) | fix: pin anyio to <4.14.0 (Python 3.13 RuntimeError) | Low | **Clean** |
| 2 | `8d804c941` (#6327) | Studio: actionable message when GGUF runtime missing | Low | **Clean** |
| 3 | `fbed3f258` (#6407) | CLI: add `unsloth connect` for coding agents | Low | **Clean** |
| 4 | `dad11e8c0` (#6602) | Fix Studio export checkpoint ordering | Low | **Clean** |
| 5 | `69d8a57ee` (#6596) | Studio: lazy-import matplotlib (server starts when wheel blocked) | Low | **Clean** |
| 6 | `b458e1cf6` (#6583) | Add HTTPS hint to Studio launch message | Low | **Clean** |

## Deferred

| # | Commit | Reason |
|---|--------|--------|
| #6568 | `6254ab37c` | Overlaps our existing `--not-secure` handling (4-file conflict in secure-flag area) |
| #6605 | `71e6b1874` | Conflict in `hub-page.tsx` |
| #6584 | `21bdc8fa8` | Conflict in `install_llama_prebuilt.py` |
| #6573 | `0689bd384` | Frontend conflicts in `chat-runtime-store.ts` / `chat-page.tsx` / `__root.tsx` (overlaps our auto-compact + Batch 2b changes) |

## Validation

- Syntax check: passed
- `test_connect.py`: **39/39 passed**
- `test_cli_studio_defaults.py`: **2/2 passed**
- `test_validate_gguf_runtime_message.py`: failed on `cryptography` native ImportError (Python 3.14 env issue, not code)

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-batch3-studio-reliability-ux`
