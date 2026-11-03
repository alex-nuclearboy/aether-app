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

Verify the installed dependency environment::

   uv pip check

Audit the current locked dependency set for known vulnerabilities::

   uv audit --preview-features audit-command --locked

Continuous integration additionally audits the locked dependency graph for
Python 3.12, 3.13, and 3.14 on Linux.

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

A username, valid email address, and password are required. This command
does not send an email verification message. See
:doc:`../security/authentication` for the account creation policy.

Inspect expired public request counters without deleting them::

   uv run python manage.py prune_public_request_counters --dry-run

Delete expired counters in batches::

   uv run python manage.py prune_public_request_counters --batch-size 1000

Verification email worker
-------------------------

Process at most one queued email using the local HTTP site origin::

   uv run python manage.py process_verification_email_queue --once --public-origin=http://127.0.0.1:8000

Run the independent worker until stopped (separate terminal or process)::

   uv run python manage.py process_verification_email_queue --public-origin=http://127.0.0.1:8000

In production, use the verified public ``https://`` origin and run the
worker as a separately supervised process. The command refuses plain HTTP
origins in production. It does not enqueue messages by itself: until the
next integration stage, registration and profile views still send messages
synchronously. Tokens and recipient addresses must not be logged.

Application
-----------

Run Django's development server::

   uv run python manage.py runserver

Static files
------------

Check static file collection without copying the files::

   uv run python manage.py collectstatic --noinput --dry-run

This command verifies the static file collection process. Core tests
separately verify the discovery of individual required assets.

Testing
-------

Run the complete test suite with coverage::

   uv run pytest

Run a specific test module::

   uv run pytest tests/test_settings.py

Run an individual test::

   uv run pytest tests/test_settings_database.py::test_expand_database_url_without_references

Quality checks
--------------

Run Django system checks::

   uv run python manage.py check

Run Pylint::

   uv run pylint config accounts core infrastructure tests manage.py docs/source/conf.py

Documentation
-------------

Build Sphinx documentation in strict mode::

   uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
