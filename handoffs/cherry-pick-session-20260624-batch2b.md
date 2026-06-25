# Cherry-Pick Session — 2026-06-24 Batch 2b (deferred retry)

**Goal:** Retry deferred #6397 by first pulling its missing dependency.
**Integration base:** `main` (at `7b2d3d04b`, after Batch 2 merge)
**Branch:** `cherry-pick/unsloth-6374-6397-html-artifacts-editable`

## Applied

| # | Commit | Subject | Risk | Applied |
|---|--------|---------|------|---------|
| 1 | `e1eaf6e20` (#6374) | Studio: HTML canvas cards in chat with auto-render, Code view, diffusion code | Medium | **Clean** |
| 2 | `9666e5de9` (#6397) | Feature: implement editable assistant messages | Medium | **Clean** (auto-merged chat-runtime-store.ts) |

## Dependency resolution

#6397 was deferred in Batch 2 because it uses `<MessageHtmlArtifacts />` from `@/components/assistant-ui/message-html-artifacts`, which did not exist in our tree. Cherry-picking #6374 first introduced that component (plus `html-fences.ts`), so #6397 then applied cleanly with only an auto-merge in `chat-runtime-store.ts`.

## Files changed

- **NEW** `studio/frontend/src/components/assistant-ui/message-html-artifacts.tsx` (#6374)
- **NEW** `studio/frontend/src/features/chat/artifacts/html-fences.ts` (#6374)
- **NEW** `studio/frontend/src/features/chat/utils/update-thread-message.ts` (#6397)
- `studio/frontend/src/components/assistant-ui/thread.tsx` (edit mode UI in both commits)
- `studio/frontend/src/features/chat/stores/chat-runtime-store.ts` (editing message state)
- `studio/frontend/src/features/chat/chat-page.tsx`, `chat-api.ts`, `chat-adapter.ts` (edit wiring)

## Validation

- `tsc -b` typecheck: **clean**
- biome: 15 errors / 37 warnings — matches existing codebase baseline (aspirational `all: true` config, not a passing gate)

## Still deferred

- `#6291` (crash recovery) — needs full manual 3-way merge preserving `_probe_mtp_decode` + `_mtp_runtime_fallback_*`
- `#6243` (free chat VRAM) — cross-cutting export-dialog modify/delete

## Branch state

Pushed to: `jecruz/unsloth:cherry-pick/unsloth-6374-6397-html-artifacts-editable`
