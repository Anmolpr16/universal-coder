# Universal Coder 2.0.0 — Final Release

Universal Coder 2.0.0 is the consolidated release of the model-agnostic coding-agent runtime.

## Supported product surfaces

- CLI (`coder run ...`)
- HTTP API with async runs and SSE streaming
- Android client
- Container deployment
- OpenAI-compatible model endpoints
- Anthropic API
- Mock provider for deterministic testing
- Native tools and stdio JSON-RPC/MCP-style tools
- Autonomous and parallel agent workflows
- Git worktree isolation and verification/repair loops

## Trust boundary

Host execution (`trusted`) is only for trusted repositories. Use `isolated` with Docker/Podman for untrusted code. For high-assurance deployments, run the service on a dedicated VM/host and expose only the intended workspace.

## Deployment acceptance

The source release is validated by the local Python test suite, compilation, package build, installation, and release audit. Docker/Podman and Android device builds are environment-specific acceptance tests and must be executed on the target deployment machine/device.

## Quick start

```bash
python -m pip install .
coder doctor
coder run "fix the failing tests"
```

For a remote service, configure authentication, TLS, workspace roots, and isolated execution before binding beyond loopback.
