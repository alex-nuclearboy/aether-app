Testing
=======

Aether uses ``pytest`` and ``pytest-django`` for automated testing.
``pytest-cov`` provides statement and branch coverage reporting.

The current test suite covers project configuration, logging configuration,
PostgreSQL integration, Django project entry points, and the accounts and
core applications.


Test structure
--------------

Project-level tests are stored in the root ``tests/`` package::

   tests/
   ├── __init__.py
   ├── test_authentication_settings.py
   ├── test_frontend.py
   ├── test_database.py
   ├── test_django_entrypoints.py
   ├── test_logging.py
   ├── test_messages.py
   ├── test_request.py
   ├── test_request_id.py
   └── test_settings.py

The current modules have separate responsibilities:

``test_authentication_settings.py``
   Checks application authentication routes and default redirect settings.

``test_frontend.py``
   Tests shared form-field markup, reusable static stylesheets, the agreed
   responsive thresholds, and base-template stylesheet inclusion.

``test_messages.py``
   Tests semantic Django message rendering, shared alert styles,
   and one-time success feedback after logout.

``test_settings.py``
   Tests runtime environment handling, Django security configuration,
   production safety validation, database URL expansion, PostgreSQL
   configuration, connection options, logging overrides, email backend
   selection, production SMTP validation, and module-level settings behaviour.

``test_database.py``
   Contains integration tests that verify the configured PostgreSQL backend
   and execute queries through Django's database connection.

``test_django_entrypoints.py``
   Contains smoke tests for the ASGI application, WSGI application, and root
   URL configuration.

``test_logging.py``
   Tests logging-level validation, development and production handlers,
   formatter selection, local log rotation, logger levels, propagation,
   and request ID filter configuration.

``test_request_id.py``
   Tests request ID generation, scope isolation, synchronous and asynchronous
   middleware execution, logging enrichment, HTTP response logging levels,
   and end-to-end authentication event correlation.

``test_request.py``
   Tests shared IP address normalisation, environment-specific client IP
   resolution, untrusted forwarded headers, and proxy-policy integration.

The root ``tests/`` package is reserved for project-wide configuration and
infrastructure tests.

Application-specific tests live inside the corresponding Django application's
own ``tests/`` package. The accounts application currently uses::

   accounts/
   └── tests/
       ├── __init__.py
       ├── test_admin.py
       ├── test_audit.py
       ├── test_backends.py
       ├── test_forms.py
       ├── test_lockout_responses.py
       ├── test_lockouts.py
       ├── test_login_ui.py
       ├── test_managers.py
       ├── test_models.py
       ├── test_validators.py
       └── test_views.py

The accounts tests cover the configured user model, Django administration,
database-level account identifier constraints, username validation rules,
case-insensitive username and email authentication, password verification,
inactive-user rejection, timing-attack mitigation, synchronous and
asynchronous authentication, inherited Django group permissions, and
brute-force protection, including lockout thresholds, identifier
normalisation, expiration, counter resets, and account/IP isolation.

``accounts/tests/test_managers.py`` checks that the custom manager requires
valid email addresses for synchronous and asynchronous user and superuser
creation, normalises email domains, and preserves standard password and
superuser behaviour.

``accounts/tests/test_models.py`` includes PostgreSQL constraint tests for
empty and whitespace-only email values, including direct ORM creation and
updates that bypass manager-level validation. Existing tests also cover
case-insensitive identifier uniqueness.

``accounts/tests/test_admin.py`` verifies that the custom user model is
registered and that the standard user-add form includes a required email
field.

``accounts/tests/test_forms.py`` checks that the application form extends
Django's authentication form, presents the username-or-email label, and
uses neutral validation text.

``accounts/tests/test_login_ui.py`` checks that the dedicated sign-in
layout includes the shared fixed header, its own logo, the login form,
and no links to authentication features that are not implemented.

``accounts/tests/test_views.py`` verifies the application login and logout
routes, public login page, shared layout, username/email sign-in, safe
redirects, CSRF protection, POST-only logout, and session invalidation.
It also verifies cross-page Axes lockouts, retry timing, and shared audit
events without reimplementing the existing account backend.

Authentication audit tests verify successful Django Admin login and logout,
anonymous logout handling, failed-login events, newly triggered lockouts,
and repeat-denial events.

They cover verified user IDs, consistent identifier fingerprints across
username and email authentication, client IP addresses, lockout duration,
UTC deadlines, remaining-time snapshots, and the absence of plaintext
credentials or duplicate threshold events.

``accounts/tests/test_lockout_responses.py`` verifies HTTP 429 responses,
recalculated ``Retry-After`` values, cache headers, and separate auditing of
blocked POST requests. Ordinary GET requests do not generate denial events.

Lockout helper tests also verify database-backed deadline calculation,
remaining time decreasing across requests, expiry, username/email identity,
and isolation by client IP. The dedicated lockout page and browser countdown
are not implemented yet and therefore are not covered by view tests.

The ``core`` application maintains a separate test package::

   core/
   └── tests/
       ├── __init__.py
       └── test_views.py

The core tests verify root URL routing, anonymous access to the home page,
shared template inheritance, the full home page logo, the clickable header
brand, and discovery of global, component-specific, and page-specific
stylesheets, logo files, and favicon assets.


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

* measures the ``config``, ``accounts``, ``core``, and ``infrastructure`` packages;
* excludes test modules and generated Django migrations;
* includes branch coverage;
* reports missing lines in the terminal;
* requires at least 90 percent overall coverage.

The threshold is a minimum quality gate rather than a target. Tests should
verify meaningful behaviour, validation paths, and integration boundaries
rather than exist solely to increase the coverage percentage.

New application packages should be added to the coverage scope when their
production code is introduced.


External integrations
---------------------

The standard automated test suite should remain deterministic and should not
depend on live third-party services.

The production email configuration is tested at the provider-neutral
configuration boundary using synthetic SMTP values. The automated test suite
does not connect to Mailjet or use real provider credentials.

Mailjet-specific SMTP connectivity and sender verification are documented
separately in :doc:`../integrations/mailjet`.

Future integrations such as Google Calendar, external APIs, and cloud storage
should normally be tested through isolated adapters, mocks, or test doubles.

Tests against real external services or deployment environments should be
introduced separately when such integration testing becomes necessary.


Continuous integration
----------------------

GitHub Actions runs the pytest suite against temporary PostgreSQL instances.

The canonical ``quality`` job uses the preferred Python version defined in
``.python-version``. Separate compatibility jobs run the same test suite on
Python 3.12 and 3.13. Together with the canonical Python 3.14 environment, this
verifies the complete supported Python range without unnecessarily repeating
the Python 3.14 test run.

Because coverage requirements are defined in ``pyproject.toml``, the same
coverage policy applies locally and to every CI test run.

See :doc:`continuous-integration` for the complete CI workflow.
