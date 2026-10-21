Code quality
============

Aether currently uses lock-file validation, installed-dependency consistency
checks, dependency vulnerability auditing, Django system checks, migration
validation, static file collection checks, automated tests with coverage
enforcement, Pylint, and a strict Sphinx build as its baseline quality checks.

Lock file
---------

Verify that ``uv.lock`` is consistent with ``pyproject.toml``::

   uv lock --check

Dependency validation
---------------------

Verify that the installed Python environment has no missing or incompatible
dependencies::

   uv pip check

This check validates the installed environment after dependency
synchronisation. It complements lock-file validation: ``uv lock --check``
verifies that the lock file is current, while ``uv pip check`` verifies the
resulting installed dependency environment.


Dependency auditing
-------------------

Audit the locked dependency graph for known vulnerabilities and adverse package
statuses::

   uv audit --preview-features audit-command --locked

The audit requires network access.

The ``audit`` command is currently a preview feature in ``uv``. Continuous
integration explicitly enables the ``audit-command`` preview feature so that
use of the experimental command is intentional rather than implicit.

CI performs separate audits for Python 3.12, 3.13, and 3.14 on Linux. This
allows environment markers and version-specific dependency selections to be
evaluated for every supported Python version.

GitHub Dependabot provides an additional repository-level monitoring layer.
Dependabot alerts can identify newly disclosed vulnerabilities independently
of the local CI run, while Dependabot security updates may prepare remediation
pull requests.

Routine Dependabot version updates are intentionally disabled.

See :doc:`continuous-integration` for the CI implementation and
:doc:`../security/dependencies` for the dependency-security policy.

Django checks
-------------

Run Django's system checks::

   uv run python manage.py check

Continuous integration additionally runs Django's deployment checks against a
synthetic production-shaped configuration::

   uv run python manage.py check --deploy --fail-level WARNING

See :doc:`continuous-integration` for the environment used by this check.

Verify that model changes have not been left without migrations::

   uv run python manage.py makemigrations --check --dry-run

Automated tests
---------------

Run the complete automated test suite::

   uv run pytest

The command also collects branch coverage and enforces the minimum coverage
threshold configured in ``pyproject.toml``.

Database-dependent tests require the local PostgreSQL service to be available.

See :doc:`testing` for the test structure, PostgreSQL testing approach, and
coverage policy.

Pylint
------

Pylint is configured in ``pyproject.toml`` with ``pylint-django`` and the
``config.settings`` Django settings module.

Generated Django migration packages are excluded from Pylint because migration
files are produced by Django rather than maintained as normal application
source code.

Run the current lint scope::

   uv run pylint config accounts core infrastructure tests manage.py docs/source/conf.py

Static files
------------

Verify that Django can discover and collect the configured static files without
copying them to the output directory::

   uv run python manage.py collectstatic --noinput --dry-run

The check covers the configured static file sources, including the project's
``static/`` directory.

The canonical GitHub Actions quality job also runs this check.

Documentation
-------------

Build the Sphinx documentation in strict mode::

   uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html

The development server does not need to be running for these checks. Commands
that initialise Django still require valid environment configuration, and
checks that connect to the database require the local PostgreSQL service to be
available.
