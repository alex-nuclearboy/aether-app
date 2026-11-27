Code quality
============

Aether currently uses lock-file validation, installed-dependency consistency
checks, dependency vulnerability auditing, Django system checks, migration
validation, static file collection checks, translation catalogue validation
and compilation, automated tests with coverage enforcement, Pylint, and a
strict Sphinx build as its baseline quality checks.

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

Translation catalogue checks
----------------------------

GNU gettext must be installed and available on ``PATH``. See
:doc:`internationalisation` for platform-specific installation instructions.
With valid Django environment configuration, run the following commands from
the repository root to inspect both catalogues for active untranslated and
fuzzy entries::

   msgattrib --untranslated --no-obsolete locale/uk/LC_MESSAGES/django.po
   msgattrib --untranslated --no-obsolete locale/pl/LC_MESSAGES/django.po
   msgattrib --only-fuzzy --no-obsolete locale/uk/LC_MESSAGES/django.po
   msgattrib --only-fuzzy --no-obsolete locale/pl/LC_MESSAGES/django.po

These commands work in Windows PowerShell and on Linux when GNU gettext is
available. Each should exit successfully without reporting any matching
entries. They inspect the catalogues without modifying them. Resolve any
reported entries before compilation. These checks do not detect user-facing
strings that have not been extracted into the catalogues.

Compile the project catalogues before the first test run after a fresh
checkout and after changes to the translation sources::

   uv run python manage.py compilemessages -l uk -l pl --ignore=.venv

The generated ``.mo`` files are ignored by Git. The canonical CI quality job
checks both catalogues for untranslated and fuzzy entries; all test-oriented
CI jobs compile the catalogues before testing. See
:doc:`continuous-integration` for the automated workflow.

Automated tests
---------------

Ensure the project translation catalogues have been compiled as described
above and that the local PostgreSQL service is available for
database-dependent tests.

Run the complete automated test suite::

   uv run pytest

The command also collects branch coverage and enforces the minimum coverage
threshold configured in ``pyproject.toml``.

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
