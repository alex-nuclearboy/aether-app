Documentation workflow
======================

Aether uses Sphinx for detailed project documentation. Sources live in
``docs/source/`` and generated HTML is written under ``docs/_build/``.

Documentation roles
-------------------

The repository documentation is deliberately split by purpose:

``README.md``
   Project entry point, requirements, quick start, current checks, and a concise
   statement of the deployment direction.

``docs/README.md``
   Contributor-facing instructions for building and maintaining the Sphinx
   documentation itself.

Sphinx documentation
   Detailed development workflows, architecture, deployment status, security,
   and reference material.

This separation keeps the root README useful without turning it into a second
copy of the full documentation.

Build locally
-------------

From the repository root::

   uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html

The build recreates the environment, reads all source files, treats warnings as
errors, warns about missing references, and prints full tracebacks when a build
fails.

The generated HTML is not committed to the repository.

Documentation policy
--------------------

Documentation should describe either implemented behaviour or an explicitly
agreed project direction. Planned provider-specific details should not be
presented as implemented behaviour.

When functionality changes, update the most specific relevant page instead of
copying the same explanation into several sections. Reference pages should stay
concise; explanatory and operational context belongs in the corresponding
development or architecture page.
