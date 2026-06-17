// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

/**
 * Pure-logic tests for client-side auto-compaction.
 *
 * The frontend has no vitest/jest harness, so these run on the Node built-in
 * test runner with native TS type-stripping:
 *
 *   node --experimental-strip-types --no-warnings --test \
 *     src/features/chat/api/auto-compact.test.ts
 *
 * `auto-compact.ts` is dependency-free (no React/zustand/`@/` imports), so it
 * strips and imports cleanly.
 */

import assert from "node:assert/strict";
import { test } from "node:test";
import {
  AUTO_COMPACT_MIN_CONTEXT,
  AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX,
  type CompactableMessage,
  compactMessages,
  decideAutoCompact,
  estimateMessagesTokens,
} from "./auto-compact.ts";

const TS = "2026-06-17T00:00:00.000Z";

function user(text: string): CompactableMessage {
  return { role: "user", content: text };
}
function assistant(text: string): CompactableMessage {
  return { role: "assistant", content: text };
}
function system(text: string): CompactableMessage {
  return { role: "system", content: text };
}

test("decideAutoCompact: disabled toggle never triggers", () => {
  const d = decideAutoCompact({
    estimatedTokens: 1_000_000,
    lastPromptTokens: 1_000_000,
    effectiveNctx: 32768,
    autoCompact: false,
  });
  assert.equal(d.trigger, false);
  assert.equal(d.reason, "disabled");
});

test("decideAutoCompact: unknown context never triggers", () => {
  for (const ctx of [null, undefined, 0]) {
    const d = decideAutoCompact({
      estimatedTokens: 99999,
      lastPromptTokens: undefined,
      effectiveNctx: ctx,
      autoCompact: true,
    });
    assert.equal(d.trigger, false);
    assert.equal(d.reason, "no_context_known");
  }
});

test("decideAutoCompact: below min context is disabled", () => {
  const d = decideAutoCompact({
    estimatedTokens: AUTO_COMPACT_MIN_CONTEXT,
    lastPromptTokens: undefined,
    effectiveNctx: AUTO_COMPACT_MIN_CONTEXT - 1,
    autoCompact: true,
  });
  assert.equal(d.trigger, false);
  assert.equal(d.reason, "below_min_context");
});

test("decideAutoCompact: triggers at/above 80% of n_ctx", () => {
  const ctx = 10000;
  const below = decideAutoCompact({
    estimatedTokens: 7999,
    lastPromptTokens: undefined,
    effectiveNctx: ctx,
    autoCompact: true,
  });
  assert.equal(below.trigger, false);
  assert.equal(below.reason, "below_threshold");

  const at = decideAutoCompact({
    estimatedTokens: 8000,
    lastPromptTokens: undefined,
    effectiveNctx: ctx,
    autoCompact: true,
  });
  assert.equal(at.trigger, true);
  assert.equal(at.reason, "above_threshold");
});

test("decideAutoCompact: prefers real lastPromptTokens (0.85x floor)", () => {
  const ctx = 10000;
  // New prompt estimate is tiny, but the previous turn was already at the
  // limit -> 0.85 * 10000 = 8500 >= 8000 trigger.
  const d = decideAutoCompact({
    estimatedTokens: 100,
    lastPromptTokens: 10000,
    effectiveNctx: ctx,
    autoCompact: true,
  });
  assert.equal(d.trigger, true);
  assert.equal(d.projectedTokens, 8500);
});

test("compactMessages: pins first system + recent pairs, drops oldest", () => {
  const messages: CompactableMessage[] = [system("SYS")];
  // 20 user/assistant pairs of ~250 tokens each (1000 chars / 4).
  const big = "x".repeat(1000);
  for (let i = 0; i < 20; i += 1) {
    messages.push(user(`${big}-u${i}`));
    messages.push(assistant(`${big}-a${i}`));
  }
  const before = estimateMessagesTokens(messages);
  const ctx = 4096; // target = 0.6 * 4096 = 2457 tokens
  const result = compactMessages({
    messages,
    effectiveNctx: ctx,
    timestamp: TS,
  });

  assert.ok(result.droppedCount > 0, "should drop something");
  assert.ok(result.usedTokens < before, "should shrink");
  // First message stays the pinned system prompt.
  assert.equal(result.messages[0]!.role, "system");
  assert.equal(result.messages[0]!.content, "SYS");
  // Synthetic marker injected as the second message.
  const marker = result.messages[1]!;
  assert.equal(marker.role, "system");
  assert.ok(
    String(marker.content).startsWith(
      AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX,
    ),
  );
  // The most-recent turn is preserved verbatim at the tail.
  const last = result.messages[result.messages.length - 1]!;
  assert.equal(last.content, `${big}-a19`);
});

test("compactMessages: keeps tool_call paired with its tool result", () => {
  const big = "y".repeat(2000);
  const messages: CompactableMessage[] = [
    system("SYS"),
    // Oldest droppable: an assistant tool_call + its tool result.
    {
      role: "assistant",
      content: big,
      tool_calls: [{ id: "call_1", type: "function" }],
    },
    { role: "tool", content: big, tool_call_id: "call_1" },
    user(big),
    assistant(big),
    user("recent"),
    assistant("recent-reply"),
  ];
  const result = compactMessages({
    messages,
    effectiveNctx: 8192,
    pinRecent: 1,
    timestamp: TS,
  });
  // No orphaned tool result should survive (a role="tool" with no preceding
  // assistant tool_call in the result).
  const roles = result.messages.map((m) => m.role);
  for (let i = 0; i < result.messages.length; i += 1) {
    if (result.messages[i]!.role === "tool") {
      const prevAssistant = result.messages
        .slice(0, i)
        .reverse()
        .find((m) => m.role === "assistant");
      assert.ok(
        prevAssistant && Array.isArray(prevAssistant.tool_calls),
        `tool result at ${i} must have a preceding assistant tool_call`,
      );
    }
  }
  assert.ok(roles.length > 0);
});

test("compactMessages: no-op returns when already under target", () => {
  const messages: CompactableMessage[] = [
    system("SYS"),
    user("hi"),
    assistant("hello"),
  ];
  const result = compactMessages({
    messages,
    effectiveNctx: 32768,
    timestamp: TS,
  });
  assert.equal(result.droppedCount, 0);
  assert.deepEqual(
    result.messages.map((m) => m.content),
    ["SYS", "hi", "hello"],
  );
});
