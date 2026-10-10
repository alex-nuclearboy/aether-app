Testing
=======

Aether uses ``pytest`` and ``pytest-django`` for automated testing.
``pytest-cov`` provides statement and branch coverage reporting.

The current test suite covers the project configuration, PostgreSQL
integration, and the Django project entry points. Application-specific tests
will be added alongside individual Django applications as those applications
are introduced.


Test structure
--------------

Project-level tests are stored in the root ``tests/`` package::

   tests/
   ├── __init__.py
   ├── test_database.py
   ├── test_django_entrypoints.py
   └── test_settings.py

The current modules have separate responsibilities:

``test_settings.py``
   Tests environment handling, database URL expansion, PostgreSQL
   configuration, validation paths, connection options, and module-level
   settings behaviour.

``test_database.py``
   Contains integration tests that verify the configured PostgreSQL backend
   and execute queries through Django's database connection.

``test_django_entrypoints.py``
   Contains smoke tests for the ASGI application, WSGI application, and root
   URL configuration.

The root ``tests/`` package is reserved for project-wide configuration and
infrastructure tests.

When a Django application is introduced, tests specific to that application
should normally live inside the application's own ``tests/`` package. For
example::

   accounts/
   └── tests/
       ├── __init__.py
       ├── test_models.py
       ├── test_urls.py
       └── test_views.py


Running tests
-------------

Start the local PostgreSQL service before running database-dependent tests::

   docker compose up -d

Run the complete test suite::

   uv run pytest

Run one test module::

   uv run pytest tests/test_settings.py

Run one individual test::

   uv run pytest tests/test_settings.py::test_expand_database_url_without_references

The standard ``pytest`` command also runs the configured coverage checks.


PostgreSQL testing
------------------

Aether uses PostgreSQL for both development and automated database tests.
SQLite is not used as a replacement test backend.

``pytest-django`` uses Django's test database infrastructure for tests that
request database access. This keeps test data separate from the normal local
development database.

Database access must be explicitly enabled, for example with the
``django_db`` marker::

   @pytest.mark.django_db
   def test_database_connection_executes_query():
       ...


Coverage
--------

Coverage is collected automatically by ``pytest-cov`` according to the
configuration in ``pyproject.toml``.

The current coverage policy:

* measures the ``config`` package;
* includes branch coverage;
* reports missing lines in the terminal;
* requires at least 90 percent overall coverage.

The threshold is a minimum quality gate rather than a target. Tests should
verify meaningful behaviour, validation paths, and integration boundaries
rather than exist solely to increase the coverage percentage.

As application packages are introduced, the coverage scope should be expanded
to include their production code.


External integrations
---------------------

The standard automated test suite should remain deterministic and should not
depend on live third-party services.

Future integrations such as Google Calendar, external APIs, and cloud storage
should normally be tested through isolated adapters, mocks, or test doubles.

Tests against real external services or deployment environments should be
introduced separately when such integration testing becomes necessary.


Continuous integration
----------------------

GitHub Actions runs the same pytest suite against the workflow's temporary
PostgreSQL service.

Because coverage requirements are defined in ``pyproject.toml``, the same
coverage policy applies locally and in continuous integration.

See :doc:`continuous-integration` for the complete CI workflow.
