# Aether documentation

The detailed Aether documentation is built with Sphinx from `docs/source/`.
The repository root `README.md` is the project entry point and quick-start guide;
Sphinx contains the longer technical, architectural, operational, and reference
material.

## Build

From the repository root, run:

```console
uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
```

The generated HTML is written to `docs/_build/html/`.

Sphinx is installed as a development dependency, so `uv sync` prepares the
documentation toolchain. The strict build treats warnings and unresolved
references as errors, matching the documentation check used in CI.

The `docs/Makefile` and `docs/make.bat` helpers are also available for local
use when preferred.

## Documentation structure

- `getting-started/` — complete local development setup and first run.
- `development/` — database operation, quality checks, CI, and documentation workflow.
- `architecture/` — current technical foundation, configuration model, and repository structure.
- `deployment/` — confirmed production target and deployment status.
- `integrations/` — confirmed integration direction without speculative implementation details.
- `security/` — current secret-handling rules.
- `reference/` — concise environment-variable and command reference.

Documentation should describe implemented behaviour or an explicitly agreed
project direction. Provider-specific details should be added only when the
corresponding implementation is introduced and verified.
