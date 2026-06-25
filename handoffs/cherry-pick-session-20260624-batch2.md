# Cherry-Pick Session — 2026-06-24 Batch 2

**Goal:** Batch 2 medium-risk Studio cherry-picks from `origin/main`.
**Integration base:** `main` (at `155e8b6ae`, after Batch 1)
**Branch:** `cherry-pick/unsloth-batch2-studio-inference-vram-editable`

## Candidates

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `bebc93d8f` (#6480) | fix(studio): handle multimodal list content in inference text paths | Medium | **Clean** |
| 2 | `6d27160dc` (#6291) | Studio: graceful recovery ladder when llama-server hard-crashes at startup | Medium | **Deferred** — conflict resolution lost the `_probe_mtp_decode` method definition; the recovery ladder calls it but the def was in a conflicted hunk that dropped. Test `test_probe_mtp_decode_returns_false_on_crash` failed with `AttributeError`. Partial landing is unsafe per policy. |
| 3 | `c42c1d56e` (#6243) | Studio: free chat model VRAM at training start only when GPU is tight | Medium | **Deferred** — 6 conflicts across backend + frontend (llama_cpp.py, inference.py, routes/inference.py, __root.tsx, chat-page.tsx, export-page.tsx) plus a modify/delete on export-dialog.tsx. Too cross-cutting to isolate safely. |
| 4 | `9666e5de9` (#6397) | Feature: implement editable assistant messages | Medium | **Deferred** — depends on `MessageHtmlArtifacts` component (`@/components/assistant-ui/message-html-artifacts`) which does not exist in our tree. Cherry-picking in isolation leaves a dangling import. |

## Applied: #6480

**Files changed:**
- `studio/backend/core/inference/message_content.py` (new — extracts text from multimodal list content)
- `studio/backend/core/inference/llama_cpp.py` (wires message_content into inference text paths)
- `studio/backend/tests/test_message_content.py` (new — 11 tests)

**Validation:**
- Syntax check: passed
- `test_message_content.py`: **11/11 passed**

## Deferred items

### #6291 — llama-server crash recovery ladder
The conflict in `llama_cpp.py` spanned the spawn block (lines ~4827-4903). Resolving by keeping the upstream recovery ladder preserved the *calls* to `_probe_mtp_decode`, `_with_flash_attn_off`, `_is_signal_crash`, and `_maybe_recover_from_mtp_crash`, but the method *definitions* and the `_mtp_runtime_fallback_*` instance attributes were in separate conflicting hunks that did not survive. Result: `AttributeError: 'LlamaCppBackend' object has no attribute '_probe_mtp_decode'`. **Recommendation:** re-attempt with a full manual 3-way merge preserving every helper method + attribute init, or wait until the branch is closer to upstream.

### #6243 — free chat VRAM at training start
Touches `llama_cpp.py`, `inference.py`, `routes/inference.py`, `routes/training.py`, `__root.tsx`, `chat-page.tsx`, `export-page.tsx`, and deletes `export-dialog.tsx` (which we still use). The export-dialog modify/delete alone makes this non-trivial. **Recommendation:** defer until the export UI has been re-synced with upstream.

### #6397 — editable assistant messages
Uses `<MessageHtmlArtifacts />` from `@/components/assistant-ui/message-html-artifacts`, a component introduced in an earlier upstream commit we have not cherry-picked. Isolating #6397 requires first pulling the commit that adds `message-html-artifacts`. **Recommendation:** identify and cherry-pick the `MessageHtmlArtifacts` introduction commit first, then retry #6397.

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-batch2-studio-inference-vram-editable`
Applied commit: `a6e8ac91e` (#6480 only)
