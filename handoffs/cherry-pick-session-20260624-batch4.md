# Cherry-Pick Session — 2026-06-24 Batch 4

**Goal:** Training/infra/loader fixes from `origin/main`.
**Integration base:** `main` (at `c470dd916`, after Batch 3 merge)
**Branch:** `cherry-pick/unsloth-batch4-training-infra-fixes`

## Applied

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `65c8a88fe` (#6575) | Studio macOS: force anyio<4.14.0 via uv override | Low | **Clean** |
| 2 | `7ecbf5a77` (#6548) | Use UTF-8 for Python code-execution subprocess I/O | Low | **Clean** |
| 3 | `48a3a7870` (#6358) | Studio: fail fast on invalid first training batch (empty chat template) | Low | **Clean** |
| 4 | `e9c574be4` (#6563) | loader: gpt-oss MXFP4 default-4bit takes MXFP4 dtype path, not BnB | Low | **Clean** |

## Deferred (conflicts)

| # | Commit | Reason |
|---|--------|--------|
| #6579 | `c9761749e` | anyio pin rationale comment conflict |
| #6560 | `52c2cf8b6` | argparse BooleanOptionalAction name conflict |
| #6551 | `ab2717afe` | trust_remote_code approval cache conflict |
| #6541 | `aeb507512` | NemotronH transformers tier conflict |
| #6550 | `007a21235` | transformers tier AutoConfig probe conflict |
| #6481 | `70926822d` | setup.sh CUDA arch detection conflict |

## Validation

- `test_exec_utf8.py`: **2/2 passed**
- `test_cli_studio_defaults.py`: **2/2 passed**
- `test_training_preflight.py`: collection error on `pyarrow` native lib (Python 3.14 env issue, not code)

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-batch4-training-infra-fixes`
