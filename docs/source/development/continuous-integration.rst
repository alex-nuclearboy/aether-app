Continuous integration
======================

GitHub Actions runs the ``Code Quality`` workflow from
``.github/workflows/code-quality.yml``.

The workflow validates the project on the preferred Python version, verifies
the additional supported Python versions, runs Django deployment checks against
a synthetic production-shaped configuration, and audits the locked dependency
graph.


Triggers
--------

The workflow runs for:

* pushes to ``main``;
* pull requests targeting ``main``.

A concurrency group cancels an older in-progress run when a newer run for the
same Git reference starts.


Workflow structure
------------------

The workflow is divided into four jobs with separate responsibilities:

* ``quality`` performs the complete project validation on the preferred Python
  version defined in ``.python-version``;
* ``python-compatibility`` verifies the additional supported Python versions;
* ``deployment-checks`` runs Django's deployment checks against a synthetic
  production-shaped configuration;
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

Both jobs explicitly classify this runtime as ``test`` through
``AETHER_ENVIRONMENT=test``. Runtime classification is independent of
``DJANGO_DEBUG``, so CI can disable Django debug mode without being mistaken
for a production environment.

The shared environment and PostgreSQL service definitions are reused inside
the workflow through YAML anchors. This keeps the CI configuration consistent
without duplicating the same environment values between jobs.

The Django secret key and PostgreSQL credentials stored in the workflow are
CI-only values. They protect only the ephemeral CI environment and are not
production secrets.

The CI database exists only for the duration of each job.


Django deployment checks
------------------------

The ``deployment-checks`` job runs separately from the test-oriented jobs.

It sets ``AETHER_ENVIRONMENT=production`` and executes:

.. code-block:: console

   uv run python manage.py check --deploy --fail-level WARNING

The job uses synthetic production-shaped environment values. These values exist
only to exercise the production configuration path and Django's deployment
checks; they do not define the final Koyeb production configuration.

No real deployment credentials are used. Database and SMTP credentials in this
job are disposable CI-only values, and the job does not connect to PostgreSQL
or the configured SMTP server.

The deployment check validates Django's production-oriented system checks,
including the production mailer configuration. This complements the normal
``quality`` and ``python-compatibility`` jobs, which continue to run with
``AETHER_ENVIRONMENT=test``.

The final Koyeb HTTPS, proxy, HSTS, database, and email configuration will be
validated separately when the production deployment is implemented.


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


Dependabot security pull requests
---------------------------------

Dependabot-generated security pull requests trigger the same
``pull_request`` workflow as other changes targeting ``main``.

A security update is therefore validated by the normal project checks,
including the canonical Python environment, the supported-Python compatibility
jobs, PostgreSQL-backed tests, Django deployment checks, and dependency
auditing.

Dependabot does not have a separate path that bypasses these checks, and
automatic merging of dependency security updates is not enabled.

Routine Dependabot version updates are intentionally disabled. Dependabot is
used for vulnerability monitoring and remediation rather than general
dependency maintenance.

See :doc:`../security/dependencies` for the complete dependency-security
policy.


Coverage
--------

Coverage requirements are configured in ``pyproject.toml`` and therefore apply
to both the canonical test run and the Python compatibility jobs.

The automated database tests use the temporary PostgreSQL service rather than
SQLite.

See :doc:`testing` for the testing and coverage policy and
:doc:`../security/dependencies` for dependency-security details.
