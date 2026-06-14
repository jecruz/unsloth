# Pinning the llama-server Inference Port

By default, Unsloth Studio auto-assigns a random free port to the internal `llama-server` process that handles GGUF inference. This document explains how to pin that port to a fixed value.

## Why Pin the Port?

A stable port number is useful when:

- **Reverse proxies** (Nginx, Traefik, Caddy) need a fixed upstream endpoint.
- **Firewall rules** or security groups must whitelist a specific port.
- **Service discovery** tools register services by port.
- **External tools** (Claude Code, Codex, custom scripts) call the OpenAI-compatible `/v1/chat/completions` endpoint at a known address.
- **Docker / container networking** maps host ports to container ports.

## How to Pin the Port

### CLI Flag

Use `--llama-server-port` with any `unsloth studio` or `unsloth studio run` command:

```bash
# Launch Studio with a pinned inference port
unsloth studio --llama-server-port 51465

# One-liner: start Studio, load a model, and pin the inference port
unsloth studio run \
  --model unsloth/Qwen3-1.7B-GGUF \
  --gguf-variant UD-Q4_K_XL \
  --llama-server-port 51465
```

### Environment Variable

Set `UNSLOTH_LLAMA_SERVER_PORT` before launching Studio. This works for both CLI and programmatic use:

```bash
export UNSLOTH_LLAMA_SERVER_PORT=51465
unsloth studio
```

On Windows PowerShell:

```powershell
$env:UNSLOTH_LLAMA_SERVER_PORT=51465
unsloth studio
```

### Direct Backend Launch

When running the backend directly without the CLI wrapper:

```bash
python studio/backend/run.py --llama-server-port 51465
```

## Validation

- The port must be an integer between **1 and 65535**.
- If an invalid value is provided, the env var is ignored and a random port is assigned.
- If the requested port is already in use when `llama-server` starts, the process fails fast rather than silently migrating to another port.

## Architecture

The port flows through the system as follows:

1. **CLI layer** (`unsloth_cli/commands/studio.py`): Accepts `--llama-server-port` and exports `UNSLOTH_LLAMA_SERVER_PORT` before re-exec or `run_server()`.
2. **Backend entry** (`studio/backend/run.py`): Reads `llama_server_port` from kwargs or argparse and sets the env var before importing the inference backend.
3. **Port allocation** (`studio/backend/core/inference/llama_cpp.py`): `_find_free_port()` checks `UNSLOTH_LLAMA_SERVER_PORT` first; if set and valid, returns it directly.
4. **Installer validation** (`studio/install_llama_prebuilt.py`): `free_local_port()` also respects the same env var during prebuilt binary validation.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `llama-server` exits with "failed to bind" | Another process already holds the port. | Choose a different port or stop the conflicting process. |
| `--llama-server-port` not recognized | Outdated CLI version. | Update via `install.sh` or `install.ps1`. |
| Port changes after model reload | Env var was not set in the process that triggered reload. | Ensure `UNSLOTH_LLAMA_SERVER_PORT` is exported in the shell or set via CLI flag. |
