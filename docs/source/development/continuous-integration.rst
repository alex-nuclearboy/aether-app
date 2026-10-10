Continuous integration
======================

GitHub Actions runs the ``Code Quality`` workflow from
``.github/workflows/code-quality.yml``.

Triggers
--------

The workflow runs for:

* pushes to ``main``;
* pull requests targeting ``main``.

A concurrency group cancels an older in-progress run when a newer run for the
same Git reference starts.

Environment
-----------

The job runs on ``ubuntu-latest`` and starts an ephemeral PostgreSQL 18 service.
The Django secret key and database credentials defined in the workflow are
disposable CI-only values; they are not production secrets.

The CI ``DATABASE_URL`` intentionally uses the same ``${...}`` references as
the local configuration. This exercises the project's database URL expansion
logic as part of the normal workflow.

Checks
------

The workflow currently:

#. checks that ``uv.lock`` is current;
#. installs the locked runtime and development dependencies;
#. runs Django system checks;
#. checks for missing migrations;
#. applies the committed migrations to PostgreSQL;
#. runs the automated test suite with coverage enforcement;
#. runs Pylint;
#. builds the Sphinx documentation in strict mode.

The automated tests use the temporary PostgreSQL service created by the
workflow. Coverage requirements come from ``pyproject.toml``, so local and CI
test runs use the same coverage policy.

This makes the CI job a validation of the project configuration, automated
tests, and the real PostgreSQL migration path rather than a lint-only
workflow.
