# Universal Coder v2.1.0

A standalone, model-agnostic autonomous coding runtime. It is intentionally independent of any single model vendor.

## Features

- Agentic observe → tool → result loop
- OpenAI-compatible provider (works with many local inference servers)
- Anthropic provider
- Mock provider for tests
- Filesystem + terminal + Git-friendly workspace
- Automatic project verification
- Snapshot/restore on failed or overlong runs
- Event bus
- Multi-agent specialist consultation (architect/tester/reviewer)
- Deterministic model routing foundation
- Autonomous planning and task decomposition
- Candidate arbitration by independent review
- End-to-end autonomous pipeline with repair and verification
- Durable run history
- Local HTTP API suitable for Android/IDE/Web clients
- CLI

## Install

```bash
python -m pip install -e .
coder run "inspect this project" --provider mock --no-verify
```

## Local model

```bash
export CODER_BASE_URL=http://127.0.0.1:11434/v1
export CODER_MODEL=llama3.1
coder run "add tests for the parser"
```

Any OpenAI-compatible local endpoint can be substituted.

## Anthropic

```bash
export CODER_API_KEY=...
coder run "fix the failing tests" --provider anthropic --model <model>
```

## Android / remote client

Run:

```bash
coder serve --host 0.0.0.0 --port 8765
```

Then call `POST /run`. See `docs/API.md`. For production, put the service behind authentication/TLS and a sandbox.


## Production installation

From a Linux or Termux checkout:

```bash
./install.sh
coder --help
```

Build a wheel locally:

```bash
python -m pip wheel . --no-build-isolation --no-deps -w dist
```

For a container deployment, copy `.env.example` to `.env`, provide a strong `CODER_AUTH_TOKEN`, mount only the intended workspace, and supply TLS certificates. The included `Dockerfile` and `docker-compose.yml` run the service as a non-root container boundary. For per-run Docker/Podman isolation, run the service on a dedicated host/VM with the selected container runtime available; mounting the host Docker socket into an application container is intentionally not recommended.

## Release acceptance

The source release must pass:

```bash
./scripts/release_audit.sh
```

The audit verifies compilation, the complete Python test suite, package metadata, wheel creation, and artifact hygiene. Docker/Podman and Android-device tests must be executed on the deployment host because those runtimes are not universally available.

## Architecture

`CLI / Android / IDE / Web -> Agent Runtime -> Provider -> Tool Registry -> Workspace -> Verification`.

The agent runtime is model-neutral; providers translate their native message/tool formats into one internal protocol.

## Release status

**v2.1.0 Release.** The repository includes the hardened core, isolated execution backend, authenticated HTTP gateway, durable runs, model abstraction, parallel agents, verification, and external tool interoperability. The release is packaged for Linux/Termux, container deployment, HTTP clients, and Android. Environment-specific acceptance tests for the chosen model provider, container runtime, and physical Android device remain deployment checks rather than source-code prerequisites.

## Multi-agent mode

```bash
coder run "refactor the parser and add regression tests" --team
```

The team mode runs independent architect, tester, and reviewer consultations in parallel, then gives their advisory synthesis to the coding agent. The coding agent remains the authority and must verify its own changes.

## V0.5 — Parallel isolated coding

V0.5 adds true parallel implementation infrastructure for Git repositories with a committed base:

```bash
coder run "refactor the parser and add regression tests" --parallel
```

Three independent implementation agents run in isolated Git worktrees. Their diffs are collected without modifying the main workspace. A selected result can be integrated after inspection:

```bash
coder run "refactor the parser" --parallel --integrate-role coder
```

The integration layer performs `git apply --check --3way` before applying a patch. This prevents an obviously conflicting patch from being applied blindly.

### Safety model

- Parallel agents never share the main working tree.
- Worktrees are removed after the run.
- No automatic merge of competing implementations occurs.
- Integration is explicit through `--integrate-role`.
- A Git repository must have a committed base before parallel mode is enabled.

## V0.6 — Autonomous pipeline

Run the full coordinator instead of manually chaining the lower-level features:

```bash
coder run "refactor the parser and add regression tests" --autonomous
```

The pipeline performs planning, parallel specialist consultation, isolated candidate implementation, independent diff arbitration, safe integration, primary-agent repair, and final verification. No automatic commit or push is performed. See `docs/V06.md`.

## V0.7 — Universal Interface Layer

V0.7 adds a transport layer around the same agent runtime so CLI, Android, IDEs, and web clients can use the same HTTP interface.

### New

- Server capabilities endpoint: `GET /capabilities`
- Server event streaming endpoint: `POST /stream` using Server-Sent Events (SSE)
- CLI event output for agent lifecycle/tool/verification events
- Provider failover routing through `--provider auto`
- Optional fallback OpenAI-compatible endpoints via `CODER_FALLBACK_URLS=url1,url2`
- Transport-neutral SSE serialization
- Android remains a thin client over the runtime rather than containing the agent itself

### Examples

```bash
coder run "fix the failing tests" --provider auto
coder serve --host 127.0.0.1 --port 8765
```

The default server bind remains localhost. Do not expose the HTTP server directly to an untrusted network without adding authentication, TLS, request limits, and workspace authorization.


## V0.9 — Universal Model Protocol

The runtime now exposes a provider-neutral model contract with capability metadata and streaming. OpenAI-compatible endpoints cover most local servers (Ollama, llama.cpp, vLLM, LM Studio and similar); Anthropic has native tool-result translation. Routing can select by capabilities and priority, with streaming failover.

The internal protocol supports:
- tool calling
- streaming
- vision capability metadata
- structured-output capability metadata
- context-window metadata
- deterministic priority routing and failover

Provider adapters are deliberately isolated from the agent runtime.


## V0.9 Tool Interoperability

Universal Coder can connect explicitly configured stdio JSON-RPC/MCP-style tool servers. External tools are discovered, namespaced by ownership, permission-gated, and routed through the same tool interface as native tools.

Example:

```bash
coder run "inspect the issue and fix it" --tool-server "python ./tools/my_server.py"
```

External commands are never chosen by the model: the user explicitly configures each server command. Use tool grants/permissions to constrain exposed tools.


## V1.0 production core

V1.0 adds authenticated HTTP execution for non-loopback deployments, bounded request/concurrency limits, asynchronous run IDs with status lookup, SSE streaming, and server-side credential handling. See `docs/V1.md`.

## Production deployment

Universal Coder has two command-execution modes:

- `trusted`: executes commands directly on the host; use only for workspaces you trust.
- `isolated`: executes commands inside Docker/Podman with CPU, memory, PID, and network controls.

For a server exposed beyond localhost, Universal Coder requires both `CODER_AUTH_TOKEN` and TLS (`CODER_TLS_CERT` + `CODER_TLS_KEY`) and automatically upgrades runs to the isolated sandbox unless explicitly running locally.

Example production configuration:

```bash
export CODER_AUTH_TOKEN='replace-with-a-long-random-token'
export CODER_TLS_CERT=/etc/universal-coder/server.crt
export CODER_TLS_KEY=/etc/universal-coder/server.key
export CODER_SANDBOX_MODE=isolated
export CODER_SANDBOX_IMAGE=python:3.12-slim
export CODER_MAX_CONCURRENT_RUNS=2
export CODER_MAX_REQUEST_BYTES=1000000
coder serve --host 0.0.0.0 --port 8765
```

Do not place provider API keys in task prompts or HTTP requests. They remain server-side environment configuration. The execution environment strips common credential-bearing environment variables before launching agent commands.

### Production boundary

The isolated executor is the recommended boundary for untrusted repositories. Docker/Podman itself must be operated with a hardened host configuration; Universal Coder does not claim that application-level policy can make a compromised container runtime safe. For high-assurance deployments, place the runtime on a dedicated VM or similarly isolated host and use least-privilege container/runtime credentials.


## Final release

Run `coder doctor` to inspect the local deployment environment. See `docs/FINAL_RELEASE.md` for the release boundary and acceptance criteria.
