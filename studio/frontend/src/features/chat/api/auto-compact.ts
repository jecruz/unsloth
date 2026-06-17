// Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

/**
 * Client-side auto-compaction logic, extracted into a dependency-free module
 * so it can be unit-tested with `node --experimental-strip-types` without
 * pulling in the React / zustand / `@/` graph that `chat-adapter.ts` carries.
 *
 * `chat-adapter.ts` re-exports every symbol here, so callers continue to
 * import from the adapter.
 *
 * Studio launches llama-server with `--no-context-shift`, so a prompt that
 * overflows the effective context window is a hard error rather than a
 * silent rolling window. These helpers decide when to compact and drop the
 * oldest non-pinned turns down to a target ratio before the send.
 */

/**
 * The structural subset of a serialized OpenAI chat message that the
 * compaction logic reads. `chat-adapter.ts`'s `SerializedMessage` is a
 * structural superset, so it is assignable to this type.
 */
export interface CompactableMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: unknown;
  tool_calls?: Array<{ id: string; [key: string]: unknown }>;
  tool_call_id?: string;
  [key: string]: unknown;
}

/**
 * Client-side auto-compaction thresholds.
 *
 * We trigger when projected prompt tokens exceed 80% of `effectiveNctx` and
 * compact down to 60%. The 20-point headroom absorbs chat-template overhead,
 * tool definitions, the synthetic summary itself, and a reasonable response
 * budget. Below 8192 tokens of context, auto-compaction is disabled because
 * the result would leave no useful working memory.
 *
 * Pin count: 4 user+assistant pairs. Anthropic / OpenAI "context editing"
 * default. Plus the first system message (always pinned) and any messages
 * with role="tool" that are still paired with an active tool_call.
 */
export const AUTO_COMPACT_TRIGGER_RATIO = 0.8;
export const AUTO_COMPACT_TARGET_RATIO = 0.6;
export const AUTO_COMPACT_PIN_RECENT = 4;
export const AUTO_COMPACT_MIN_CONTEXT = 8192;
export const AUTO_COMPACT_SUMMARY_MAX_TOKENS = 400;
export const AUTO_COMPACT_MAX_RETRIES = 1;
export const AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX = "[compacted ";

export type CompactMode = "truncate" | "summarize";

/** char/4 token estimate; mirrors chat-adapter's `estimateTokenCount`. */
function estimateTokenCount(text: string): number {
  const trimmed = text.trim();
  if (!trimmed) return 0;
  return Math.max(1, Math.round(trimmed.length / 4));
}

/**
 * Count the tokens of a single serialized message by walking its content.
 * The structured-content branch sums across text parts and uses a 1.6x
 * correction factor for image / audio bytes, which empirically matches
 * what multimodal payloads cost in llama-server (where image tokens are
 * roughly 1.5-2x the raw base64 size in tokens).
 */
export function estimateMessageTokens(message: CompactableMessage): number {
  const content = message.content;
  if (typeof content === "string") {
    return estimateTokenCount(content);
  }
  if (!Array.isArray(content)) {
    return 0;
  }
  let total = 0;
  for (const part of content) {
    if (!part || typeof part !== "object") continue;
    const p = part as Record<string, unknown>;
    if (p.type === "text" && typeof p.text === "string") {
      total += estimateTokenCount(p.text);
    } else if (p.type === "image_url" || p.type === "input_audio") {
      const dataUrl =
        typeof p.image_url === "object" && p.image_url
          ? String((p.image_url as Record<string, unknown>).url ?? "")
          : typeof p.input_audio === "object" && p.input_audio
            ? String((p.input_audio as Record<string, unknown>).data ?? "")
            : "";
      total += Math.max(1, Math.round((dataUrl.length / 4) * 1.6));
    }
  }
  return total;
}

/**
 * Sum estimated tokens across a list of serialized messages. Mirrors the
 * pre-send prompt size (chat-template + tool definitions live outside this
 * list, so callers should add 1-3k of headroom when comparing to n_ctx).
 */
export function estimateMessagesTokens(
  messages: ReadonlyArray<CompactableMessage>,
): number {
  let total = 0;
  for (const message of messages) {
    total += estimateMessageTokens(message);
  }
  return total;
}

export interface AutoCompactDecision {
  /** Whether to compact before sending this turn. */
  trigger: boolean;
  /** Human-readable reason (for telemetry, logs, and the post-compact toast). */
  reason:
    | "above_threshold"
    | "below_threshold"
    | "below_min_context"
    | "disabled"
    | "no_context_known";
  /** The projected prompt size that triggered the decision. */
  projectedTokens: number;
  /** The effective n_ctx used for the ratio check (or 0 if unknown). */
  effectiveNctx: number;
}

/**
 * Decide whether the next send should auto-compact.
 *
 * Prefers the real `lastPromptTokens` from the previous turn's usage
 * metadata (already plumbed through `contextUsage.promptTokens`) over a
 * fresh char/4 estimate. The 0.85x floor on `lastPromptTokens` covers the
 * case where the *new* user turn is much smaller than the previous one
 * (e.g. user pasted a long file last turn, now sent a one-line follow-up)
 * -- we still want to compact if the *baseline* is already at the limit,
 * but only when the new prompt is at least 85% of the previous size.
 */
export function decideAutoCompact(args: {
  estimatedTokens: number;
  lastPromptTokens: number | undefined;
  effectiveNctx: number | null | undefined;
  autoCompact: boolean;
}): AutoCompactDecision {
  const { estimatedTokens, lastPromptTokens, effectiveNctx, autoCompact } =
    args;
  const ctx = effectiveNctx ?? 0;
  if (!autoCompact) {
    return {
      trigger: false,
      reason: "disabled",
      projectedTokens: estimatedTokens,
      effectiveNctx: ctx,
    };
  }
  if (!ctx || ctx <= 0) {
    return {
      trigger: false,
      reason: "no_context_known",
      projectedTokens: estimatedTokens,
      effectiveNctx: ctx,
    };
  }
  if (ctx < AUTO_COMPACT_MIN_CONTEXT) {
    return {
      trigger: false,
      reason: "below_min_context",
      projectedTokens: estimatedTokens,
      effectiveNctx: ctx,
    };
  }
  const projected = lastPromptTokens
    ? Math.max(Math.round(lastPromptTokens * 0.85), estimatedTokens)
    : estimatedTokens;
  if (projected / ctx >= AUTO_COMPACT_TRIGGER_RATIO) {
    return {
      trigger: true,
      reason: "above_threshold",
      projectedTokens: projected,
      effectiveNctx: ctx,
    };
  }
  return {
    trigger: false,
    reason: "below_threshold",
    projectedTokens: projected,
    effectiveNctx: ctx,
  };
}

/**
 * Compact a serialized message list down to fit in `effectiveNctx`.
 *
 * Strategy:
 *   1. Always pin the first system message (if any).
 *   2. Pin the last AUTO_COMPACT_PIN_RECENT user+assistant pairs verbatim.
 *   3. Drop the oldest non-pinned turns. When dropping an assistant turn that
 *      carries tool_calls, drop the following tool results tied to those calls
 *      together with it (never leave a tool_call with no following tool result,
 *      or a tool result with no preceding tool_call -- that would break the
 *      OpenAI/Anthropic protocol).
 *   4. Replace the dropped prefix with a synthetic system message carrying
 *      the AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX, the drop count, the
 *      current ISO-8601 timestamp, and (optionally) the model-generated
 *      summary in "summarize" mode.
 *   5. Walk the result until projected tokens <= effectiveNctx *
 *      AUTO_COMPACT_TARGET_RATIO. We never go below the pinned floor
 *      (system + pin recent), even if the result is still over budget --
 *      in that case the next turn will trigger the llama-server
 *      `--no-context-shift` error path as the safety net.
 */
export function compactMessages<T extends CompactableMessage>(args: {
  messages: ReadonlyArray<T>;
  effectiveNctx: number;
  summary?: string;
  /** ISO-8601 timestamp injected into the synthetic marker. Defaults to now. */
  timestamp?: string;
  /** Override pin count for tests; defaults to AUTO_COMPACT_PIN_RECENT. */
  pinRecent?: number;
}): {
  messages: T[];
  droppedCount: number;
  usedTokens: number;
  targetTokens: number;
} {
  const {
    messages,
    effectiveNctx,
    summary,
    timestamp = new Date().toISOString(),
    pinRecent = AUTO_COMPACT_PIN_RECENT,
  } = args;

  // 1. Identify the pinned first system message (if any).
  const firstSystemIdx = messages.findIndex((m) => m.role === "system");
  const firstSystem = firstSystemIdx >= 0 ? messages[firstSystemIdx]! : null;

  // 2. Identify the pinned recent N user+assistant pairs. Walk backwards
  // from the tail, counting user messages, until we have pinRecent.
  const tail: T[] = [];
  let userCount = 0;
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    // Stop before the pinned first system message; it is added separately, so
    // letting the tail swallow it would duplicate it in the result.
    if (firstSystemIdx >= 0 && i <= firstSystemIdx) break;
    const m = messages[i];
    if (!m) continue;
    if (m.role === "user") {
      if (userCount >= pinRecent) break;
      userCount += 1;
    }
    tail.unshift(m);
  }
  const tailStartIdx =
    tail.length > 0 ? messages.indexOf(tail[0]!) : messages.length;

  // 3. The drop window is everything between the pinned system message and
  // the pinned tail.
  const dropWindow =
    firstSystemIdx >= 0
      ? messages.slice(firstSystemIdx + 1, tailStartIdx)
      : messages.slice(0, tailStartIdx);

  // 4. Drop the drop window iteratively until we hit the target ratio.
  const targetTokens = Math.max(
    1,
    Math.floor(effectiveNctx * AUTO_COMPACT_TARGET_RATIO),
  );

  const keptWindow: T[] = [...dropWindow];
  let droppedFromWindow = 0;
  while (keptWindow.length > 0) {
    const withSystem = firstSystem
      ? [firstSystem, ...keptWindow, ...tail]
      : [...keptWindow, ...tail];
    const used = estimateMessagesTokens(withSystem);
    if (used <= targetTokens) break;
    // Drop the oldest message in the window. If it is an assistant turn with
    // tool_calls, also drop any immediately-following tool results that
    // reference those call ids so we never orphan a tool_call.
    const first = keptWindow[0]!;
    if (first.role === "assistant" && Array.isArray(first.tool_calls)) {
      const callIds = new Set(
        first.tool_calls.map((c) => c?.id).filter(Boolean),
      );
      let dropUntil = 1;
      while (dropUntil < keptWindow.length) {
        const m = keptWindow[dropUntil];
        if (
          m?.role === "tool" &&
          typeof m.tool_call_id === "string" &&
          callIds.has(m.tool_call_id)
        ) {
          dropUntil += 1;
        } else {
          break;
        }
      }
      droppedFromWindow += keptWindow.splice(0, dropUntil).length;
    } else {
      keptWindow.shift();
      droppedFromWindow += 1;
    }
  }

  // 5. Assemble the result. If anything was dropped, prepend the synthetic
  // system message after the pinned first system.
  const result: T[] = [];
  if (firstSystem) result.push(firstSystem);
  if (droppedFromWindow > 0) {
    const summaryLine = summary?.trim();
    const text = summaryLine
      ? `${AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX}${droppedFromWindow} turns at ${timestamp}]\n${summaryLine}`
      : `${AUTO_COMPACT_SYNTHETIC_SYSTEM_MARKER_PREFIX}${droppedFromWindow} turns at ${timestamp}]\nEarlier turns were compacted to fit the context window.`;
    result.push({ role: "system", content: text } as T);
  }
  result.push(...keptWindow, ...tail);

  // 6. Report usage for the post-compact toast and the context-usage bar.
  const usedTokens = estimateMessagesTokens(result);
  return {
    messages: result,
    droppedCount: droppedFromWindow,
    usedTokens,
    targetTokens,
  };
}
