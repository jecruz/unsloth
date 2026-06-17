#!/usr/bin/env bash
# Local smoke-test wrapper for the Qwen3.6-27B-MTP GGUF on M3 Ultra.
# Hardcodes the user's local install layout; not portable. The MTP spec
# args here match the ones the fork auto-emits, so the wrapper is a
# reproducer for the same config Studio would build.
set -euo pipefail
exec /Users/jeffreycruz/.unsloth/llama.cpp/llama-server \
    -m /Volumes/StudioStackSSD4TB/Development/LLM/huggingface/hub/models--unsloth--Qwen3.6-27B-MTP-GGUF/snapshots/5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace/Qwen3.6-27B-UD-Q4_K_XL.gguf \
    --port 51465 \
    -c 262144 \
    --parallel 1 \
    --flash-attn on \
    --no-context-shift \
    --fit on \
    --threads -1 \
    --jinja \
    --spec-type ngram-mod,draft-mtp \
    --spec-draft-n-max 3 \
    --spec-ngram-mod-n-match 24 \
    --spec-ngram-mod-n-min 48 \
    --spec-ngram-mod-n-max 64 \
    --chat-template-kwargs '{"enable_thinking": true, "preserve_thinking": false}' \
    --mmproj /Volumes/StudioStackSSD4TB/Development/LLM/huggingface/hub/models--unsloth--Qwen3.6-27B-MTP-GGUF/snapshots/5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace/mmproj-F16.gguf