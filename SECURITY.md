# Security Policy

Universal Coder executes model-generated commands and edits files. Treat it as privileged automation.

## Required production controls

- Run untrusted repositories with `CODER_SANDBOX_MODE=isolated`.
- Prefer a dedicated VM/host for the service.
- Set `CODER_AUTH_TOKEN` and TLS for non-loopback HTTP service.
- Set `CODER_WORKSPACE_ROOTS` to an explicit allowlist of directories.
- Do not expose provider credentials to task environments.
- Keep Docker/Podman patched and use least-privilege runtime access.

## Threat model

Application-level command filters are defense-in-depth only. Container isolation is the primary execution boundary. A container runtime or host compromise is outside the application's security boundary.

## Reporting

Do not disclose exploitable vulnerabilities publicly before a fix is available. Report the issue privately to the project maintainer with reproduction steps and impact.
