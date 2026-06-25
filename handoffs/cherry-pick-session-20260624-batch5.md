# Cherry-Pick Session — 2026-06-24 Batch 5

**Goal:** Studio UX cleanup + backend reliability fixes.
**Integration base:** `main` (at `42190c960`, after Batch 4 merge)
**Branch:** `cherry-pick/unsloth-batch5-studio-ux-cleanup`

## Applied

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `3a9fc34fc` (#6576) | Studio Playwright: snooze update banner before sending | Low | **Clean** |
| 2 | `707641179` (#6420) | Align GRPO vllm_enable_sleep_mode with engine sleep state | Low | **Clean** |
| 3 | `892d2983b` (#6413) | Fix scan_packages.py --fix crash on download_packages() tuple return | Low | **Clean** |
| 4 | `b0b27c938` (#6390) | Shim removed vllm.transformers_utils.tokenizer for vLLM >= 0.22 | Low | **Clean** |
| 5 | `93572648b` (#6433) | Studio Hub: default downloads to Xet transport | Low | **Clean** |
| 6 | `a74ba71c0` (#6394) | Studio: convert SecurityHeadersMiddleware to pure ASGI | Low | **Clean** |
| 7 | `f5f9e217c` (#6400) | studio: select torchao version from installed torch | Low | **Clean** |
| 8 | `dc2e5abd3` (#6398) | Studio: surface the real reason a model fails validation | Low | **Clean** |

## Deferred (conflicts)

| # | Commit | Reason |
|---|--------|--------|
| #6585 | `1cc785e5a` | remove unused packages conflict |
| #6606 | `88e451c63` | hub avatar conflict |
| #6607 | `9776bac2b` | reasoning icon conflict |
| #6594 | `2193b7f31` | remember-settings per quant conflict |
| #6572 | `a2423e614` | hide RAG embedder conflict |
| #6591 | `76cbddb85` | --secure with --api-only conflict |
| #6578 | `ce0323263` | test isolation conflict |
| #6582 | `7bac46147` | git blame ignore revs conflict |
| #6391 | `0533efe3f` | harden model fetching conflict |
| #6393 | `a35fbe22e` | serialize non-streaming responses conflict |
| #6377 | `9a966adf5` | trim serving-log noise conflict |

## Validation

- `test_torchao_select.py` + `test_middleware.py`: **21 passed**, 1 error (cryptography native lib ImportError on Python 3.14 — env issue)
- `test_cli_studio_defaults.py`: **2/2 passed**

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-batch5-studio-ux-cleanup`
HANDOFF
git add handoffs/cherry-pick-session-20260624-batch5.md && git commit -m "cherry-pick: Batch 5 Studio UX cleanup + backend reliability

Applied 8 low-risk cherry-picks from origin/main:

  #6576  Studio Playwright: snooze update banner
  #6420  Align GRPO vllm_enable_sleep_mode with engine state
  #6413  Fix scan_packages --fix crash on tuple return
  #6390  Shim removed vllm tokenizer for vLLM >= 0.22
  #6433  Studio Hub: default downloads to Xet transport
  #6394  SecurityHeadersMiddleware to pure ASGI
  #6400  select torchao version from installed torch
  #6398  surface real model validation failure reason

Deferred (11 conflicts): #6585, #6606, #6607, #6594, #6572, #6591,
#6578, #6582, #6391, #6393, #6377.

Validation: 21 torchao/middleware tests pass, 2/2 CLI defaults." 2>&1 | tail -3 && echo "=== PUSH ===" && SKIP_CODE_REVIEW=1 git push -u fork cherry-pick/unsloth-batch5-studio-ux-cleanup 2>&1 | tail -3
