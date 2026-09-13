# Contributing

1. Create a branch.
2. Keep provider-specific behavior inside `src/universal_coder/providers`.
3. Keep tool permissions explicit and fail closed for new capabilities.
4. Add tests for every behavior change.
5. Run `./scripts/release_check.sh` before opening a pull request.
6. Do not commit API keys, certificates, private model endpoints, runtime state, or generated artifacts.
