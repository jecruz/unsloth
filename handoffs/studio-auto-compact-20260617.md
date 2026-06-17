# Handoff — Studio Client-Side Auto-Compact

**Date:** 2026-06-17
**Branch:** `feature/studio-auto-compact` (from `main` @ `688172bcb`)

## What & Why

Studio launches llama-server with `--no-context-shift`
(`studio/backend/core/inference/llama_cpp.py`), so a chat that exceeds the
effective context window fails hard instead of rolling the window. Previously
the only client behavior on overflow was a "Context limit reached" toast
(`chat-adapter.ts` `isContextLimitError`) telling the user to raise Context
Length. There was **no auto-compaction**.

This adds **client-side auto-compaction, ON by default**, for the local
llama-server path only. External providers manage their own context and are
skipped.

## Design (pinned constants)

In `studio/frontend/src/features/chat/api/auto-compact.ts`:

- `AUTO_COMPACT_TRIGGER_RATIO = 0.8` — compact when projected prompt ≥ 80% of effective n_ctx
- `AUTO_COMPACT_TARGET_RATIO = 0.6` — compact down to 60%
- `AUTO_COMPACT_PIN_RECENT = 4` — keep last 4 user+assistant pairs verbatim
- `AUTO_COMPACT_MIN_CONTEXT = 8192` — disable below this n_ctx
- `AUTO_COMPACT_SUMMARY_MAX_TOKENS = 400`, `AUTO_COMPACT_MAX_RETRIES = 1` — reserved for summarize mode
- `AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX = "[compacted "` — marker on the synthetic system message
- `CompactMode = "truncate" | "summarize"`, default `"truncate"`

Token estimate: prefers the real `contextUsage.promptTokens` from the prior
turn's usage metadata (with a 0.85x floor) over the char/4 estimate.

Compaction strategy: pin first system message + recent N pairs, drop oldest
non-pinned turns down to the target ratio, keep assistant `tool_calls` paired
with their `tool` results, and prepend a synthetic system marker noting the
drop count + timestamp.

## Files Changed

- **NEW** `api/auto-compact.ts` — dependency-free pure logic (constants,
  `estimateMessageTokens`, `estimateMessagesTokens`, `decideAutoCompact`,
  `compactMessages`, `CompactableMessage`/`CompactMode`/`AutoCompactDecision`).
  Extracted into its own module specifically so it can be unit-tested with
  `node --experimental-strip-types` without dragging in React/zustand/`@/`.
- **NEW** `api/auto-compact.test.ts` — 8 `node:test` cases (decision gating,
  0.85x floor, system+recent pinning, tool-call pairing, no-op path).
- `api/chat-adapter.ts` — re-exports the module symbols (back-compat) and adds
  the send preflight after the system prompt is built (~line 1780): runs only
  when `!isExternalRequest`, splices compacted messages back into
  `outboundMessages`, and toasts the dropped count.
- `stores/chat-runtime-store.ts` — new `autoCompact` (default true) +
  `compactMode` (default "truncate") state, setters, and localStorage
  persistence (`unsloth_chat_auto_compact`, `unsloth_chat_compact_mode`).
- `chat-settings-sheet.tsx` — `AutoCompactToggle` row in the (local-only)
  Tools section, next to `AutoHealToolCallsToggle`.

## Validation

- `node --experimental-strip-types --no-warnings --test src/features/chat/api/auto-compact.test.ts` → **8/8 pass**
- `npm run typecheck` (`tsc -b`) → **clean**
- `biome check` on changed files → only the same `style/all`/`complexity/all`
  advisories the existing `chat-adapter.ts` already emits (the repo biome
  config is `all: true`, aspirational, not a passing gate). New files were run
  through `biome check --write` for safe autofixes.

## Known Gaps / Next Steps

- **Summarize mode is plumbed but not wired.** `compactMode` state +
  `summary` param on `compactMessages` exist, but the preflight always uses
  truncate. Wiring summarize needs an extra model round-trip (summarize the
  dropped prefix) before the main send + a `compactMode` UI selector. Toggle
  currently only exposes on/off.
- Pre-existing unrelated test flake (NOT from this work):
  `unsloth_cli/tests/test_studio_secure_flag.py::test_run_in_venv_passes_secure_and_forces_host`
  fails identically at `e591faf55` (venv subprocess monkeypatch resolution).
- No frontend test runner exists (only biome/eslint/tsc); the `node:test`
  approach is the lightweight path. Consider a `test:unit` npm script if more
  pure-logic suites land.
