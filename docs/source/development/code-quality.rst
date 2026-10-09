Code quality
============

Aether currently uses lock-file validation, Django system checks, migration
validation, Pylint, and a strict Sphinx build as its baseline local quality
checks.

Lock file
---------

Verify that ``uv.lock`` is consistent with ``pyproject.toml``::

   uv lock --check

Django checks
-------------

Run Django's system checks::

   uv run python manage.py check

Verify that model changes have not been left without migrations::

   uv run python manage.py makemigrations --check --dry-run

Pylint
------

Pylint is configured in ``pyproject.toml`` with ``pylint-django`` and the
``config.settings`` Django settings module.

Run the current lint scope::

   uv run pylint config manage.py docs/source/conf.py

Documentation
-------------

Build the Sphinx documentation in strict mode::

   uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html

The development server does not need to be running for these checks. Commands
that initialise Django still require valid environment configuration, and
checks that connect to the database require the local PostgreSQL service to be
available.

Automated tests and dependency auditing are not part of the current baseline
and should be documented here when they are introduced.
