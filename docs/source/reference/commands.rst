Project commands
================

This page is a compact command reference. For context and expected behaviour,
follow the links from the relevant development section.

Dependencies
------------

Synchronise runtime and development dependencies::

   uv sync

Verify that the lock file is current::

   uv lock --check

Local database
--------------

Start PostgreSQL::

   docker compose up -d

Inspect service status::

   docker compose ps

Read database logs::

   docker compose logs db

Stop the local PostgreSQL service while preserving the named volume::

   docker compose down

Django database
---------------

Apply migrations::

   uv run python manage.py migrate

Check for missing migrations::

   uv run python manage.py makemigrations --check --dry-run

Create a local superuser::

   uv run python manage.py createsuperuser

Application
-----------

Run Django's development server::

   uv run python manage.py runserver

Testing
-------

Run the complete test suite with coverage::

   uv run pytest

Run a specific test module::

   uv run pytest tests/test_settings.py

Run an individual test::

   uv run pytest tests/test_settings.py::test_expand_database_url_without_references

Quality checks
--------------

Run Django system checks::

   uv run python manage.py check

Run Pylint::

   uv run pylint config tests manage.py docs/source/conf.py

Documentation
-------------

Build Sphinx documentation in strict mode::

   uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
