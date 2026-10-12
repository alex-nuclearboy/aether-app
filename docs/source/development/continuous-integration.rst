Continuous integration
======================

GitHub Actions runs the ``Code Quality`` workflow from
``.github/workflows/code-quality.yml``.

The workflow validates the preferred development environment, verifies the
additional supported Python versions, and audits the locked dependency graph.


Triggers
--------

The workflow runs for:

* pushes to ``main``;
* pull requests targeting ``main``.

A concurrency group cancels an older in-progress run when a newer run for the
same Git reference starts.


Workflow structure
------------------

The workflow is divided into three jobs with separate responsibilities:

* ``quality`` performs the complete project validation on the preferred Python
  version defined in ``.python-version``;
* ``python-compatibility`` verifies the additional supported Python versions;
* ``security`` audits the dependency graph for known vulnerabilities and
  adverse package statuses.


Quality job
-----------

The ``quality`` job uses the Python version defined in ``.python-version`` and
runs against an ephemeral PostgreSQL 18 service.

It performs the complete project validation:

#. checks that ``uv.lock`` is current;
#. installs the locked runtime and development dependencies;
#. verifies the installed dependency environment with ``uv pip check``;
#. runs Django system checks;
#. checks for missing migrations;
#. applies the committed migrations to PostgreSQL;
#. runs the automated test suite with coverage enforcement;
#. runs Pylint;
#. builds the Sphinx documentation in strict mode.

This is the canonical CI environment for the project.


Python compatibility
--------------------

Aether supports Python 3.12, 3.13, and 3.14.

The preferred Python 3.14 environment is already exercised by the ``quality``
job. The ``python-compatibility`` matrix therefore tests only Python 3.12 and
3.13 rather than repeating the same functional checks for Python 3.14.

Each compatibility job:

#. installs the locked dependencies for the selected Python version;
#. reports the actual Python version used by the job;
#. verifies the installed dependency environment with ``uv pip check``;
#. runs Django system checks;
#. applies the committed migrations to PostgreSQL;
#. runs the automated test suite with coverage enforcement.

Pylint and Sphinx are not repeated in the compatibility matrix because they
are already validated by the canonical ``quality`` job. The purpose of the
matrix is runtime compatibility rather than duplicate code-quality checks.


Shared test environment
-----------------------

The ``quality`` and ``python-compatibility`` jobs use the same disposable
Django and PostgreSQL configuration.

The shared environment and PostgreSQL service definitions are reused inside
the workflow through YAML anchors. This keeps the CI configuration consistent
without duplicating the same environment values between jobs.

The Django secret key and PostgreSQL credentials stored in the workflow are
CI-only values. They protect only the ephemeral CI environment and are not
production secrets.

The CI database exists only for the duration of each job.


Dependency security
-------------------

The ``security`` job does not require Django configuration or a PostgreSQL
service.

It validates the lock file and audits the dependency graph for:

* Python 3.12 on Linux;
* Python 3.13 on Linux;
* Python 3.14 on Linux.

The audit uses ``uv audit`` with ``--locked``, ``--python-version``, and
``--python-platform linux``.

The requested Python version controls the dependency set being audited. It
does not mean that ``uv`` itself must be running under that interpreter. For
example, the command may report the preferred project interpreter while still
auditing the dependency graph selected for Python 3.12.

The ``uv audit`` command is currently a preview feature. The job explicitly
sets::

   UV_PREVIEW_FEATURES=audit-command

to acknowledge and enable that preview feature without emitting the preview
warning.

A vulnerability or adverse package status reported by the audit causes the
corresponding CI step to fail.


Coverage
--------

Coverage requirements are configured in ``pyproject.toml`` and therefore apply
to both the canonical test run and the Python compatibility jobs.

The automated database tests use the temporary PostgreSQL service rather than
SQLite.

See :doc:`testing` for the testing and coverage policy and
:doc:`../security/dependencies` for dependency-security details.
