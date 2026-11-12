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
   ├── test_password_reset_logging.py
   ├── test_request.py
   ├── test_request_id.py
   ├── settings_helpers.py
   ├── test_settings.py
   ├── test_settings_database.py
   ├── test_settings_email.py
   ├── test_settings_registration.py
   ├── test_settings_security.py
   └── test_template_translations.py

The current modules have separate responsibilities:

``test_authentication_settings.py``
   Checks application authentication routes and default redirect settings.

``test_frontend.py``
   Tests shared form-field markup, help text and validation-error ARIA
   associations, reusable static stylesheets, the agreed responsive
   thresholds, and base-template stylesheet inclusion.

``test_template_translations.py``
   Checks HTML language attributes on rendered pages and verification email
   templates, as well as translation markers in shared UI templates.

``test_messages.py``
   Tests semantic Django message rendering, shared alert styles,
   and one-time success feedback after logout.

``settings_helpers.py``
   Provides synthetic environments, isolated settings-module execution,
   explicit registration-flag defaults, and reusable PostgreSQL helpers.

``test_settings.py``
   Tests environment-file loading, core settings validation, and logging
   overrides.

``test_settings_database.py``
   Tests database URL expansion, PostgreSQL-only validation, and connection
   options.

``test_settings_security.py``
   Tests environment validation, production security requirements,
   HTTPS-related settings, and client IP resolution.

``test_settings_email.py``
   Tests development and production email backends and SMTP configuration.

``test_settings_registration.py``
   Tests the registration flag's actual default without a local ``.env``,
   explicit disabled and enabled states, and rejection of production opt-in.
   Other settings tests force the registration flag off to avoid dependence
   on the developer's local ``.env`` file.

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
   verification-path masking before routing (including redirects and 404s),
   and end-to-end authentication event correlation.

``test_password_reset_logging.py``
   Tests pre-routing reset-token masking, redaction of formatted Django log
   messages, plain/coloured formatters and the production/development
   logging configuration.

``test_request.py``
   Tests shared IP address normalisation, environment-specific client IP
   resolution, untrusted forwarded prefixes, failure-closed handling of
   missing and invalid production headers, and proxy-policy integration.

The root ``tests/`` package is reserved for project-wide configuration and
infrastructure tests.

Application-specific tests live inside the corresponding Django application's
own ``tests/`` package. The accounts application currently uses::

   accounts/
   └── tests/
       ├── __init__.py
       ├── registration_helpers.py
       ├── test_admin.py
       ├── test_audit.py
       ├── test_backends.py
       ├── test_commands.py
       ├── test_email_outbox.py
       ├── test_email_worker.py
       ├── test_email_worker_command.py
       ├── test_email_verification.py
       ├── test_forms.py
       ├── test_interface_translations.py
       ├── test_lockout_responses.py
       ├── test_lockouts.py
       ├── test_login_ui.py
       ├── test_managers.py
       ├── test_models.py
       ├── test_password_reset.py
       ├── test_password_reset_worker.py
       ├── test_profile_verification.py
       ├── test_public_email_correction.py
       ├── test_public_rate_limits.py
       ├── test_public_request_counter_cleanup.py
       ├── test_registration_flow.py
       ├── test_registration_form.py
       ├── test_registration_page.py
       ├── test_registration_service.py
       ├── test_registration_throttle.py
       ├── test_validators.py
       └── test_views.py

The accounts tests cover the configured user model, Django administration,
database-level account identifier constraints, username validation rules,
case-insensitive username and email authentication, password verification,
inactive-user rejection, verification-required login restrictions,
timing-attack mitigation, synchronous and asynchronous authentication,
inherited Django group permissions, and
brute-force protection, including lockout thresholds, identifier
normalisation, expiration, counter resets, and account/IP isolation.

``accounts/tests/test_managers.py`` checks that the custom manager requires
valid email addresses for synchronous and asynchronous user and superuser
creation, normalises email domains, and preserves standard password and
superuser behaviour.

``accounts/tests/test_models.py`` includes PostgreSQL constraint tests for
empty and whitespace-only email values, including direct ORM creation and
updates that bypass manager-level validation. Existing tests also cover
case-insensitive identifier uniqueness, default-unverified email state,
persisted verification, case-insensitive matching, changes of email address,
independence from ``is_active``, non-editability of verification fields,
and default access for accounts created by the manager and superuser tools.

``accounts/tests/test_backends.py`` additionally verifies that public-style
accounts are rejected before email verification and permitted afterwards,
including both login identifiers, asynchronous authentication, email changes,
and continued rejection of inactive users.

``accounts/tests/test_email_outbox.py`` checks outbox reservations,
recipient snapshots, status and cooldown handling, duplicate active jobs,
changed email addresses and rollback of both job and request timestamp.
It does not exercise a worker or SMTP delivery.

``accounts/tests/test_email_worker.py`` checks independent SMTP
delivery, public-origin validation, stale-recipient and inactive-account
cancellation (including retries), bounded retry delays, expired leases and
compare-and-swap completion.

``accounts/tests/test_email_worker_command.py`` covers one-shot command
execution, idle queues, invalid polling intervals and missing origins.

``accounts/tests/test_profile_verification.py`` checks that authenticated
profile POSTs enqueue instead of sending synchronously, do not accept a
recipient override, handle active jobs and cooldown, and leave SMTP retries
to the worker. It also covers confirmation and CSRF behaviour.

``accounts/tests/test_email_verification.py`` covers token validity,
expiration, account binding, email and password changes, invalidation
after verification, malformed tokens, transaction-safe state updates,
repeated confirmation attempts, unknown users, and independence from
account activation.

``accounts/tests/test_admin.py`` verifies that the custom user model is
registered and that the standard user-add form includes a required email
field, rejects missing or malformed addresses, and accepts a valid address.

``accounts/tests/test_commands.py`` verifies ``createsuperuser`` in
non-interactive mode, including successful creation with a valid email,
rejection of missing or malformed addresses, and preservation of standard
superuser permissions.

``accounts/tests/test_forms.py`` checks that the application form extends
Django's authentication form, presents the username-or-email label, and
uses neutral validation text.

``accounts/tests/registration_helpers.py`` supplies shared, synthetic
registration form data to both registration test modules.

``accounts/tests/test_registration_form.py`` checks required fields,
case-insensitive identifier uniqueness, username syntax, email
normalisation, Django's standard password validation and confirmation,
error codes, and the email-verification-required policy on form saves.

``accounts/tests/test_registration_page.py`` verifies the registration GET
form, enabled and disabled POST behaviour, form field errors, uniqueness
conflict feedback, account and job creation without HTTP SMTP, CSRF checks,
the token-free result page, localised HTML language metadata, and
authenticated-user redirects.

``accounts/tests/test_registration_flow.py`` uses a worker-delivered link
to exercise registration, refusal of sign-in before confirmation, the
read-only confirmation GET, confirmation POST, and sign-in by username or
email.

``accounts/tests/test_public_rate_limits.py`` checks PostgreSQL-backed
fixed-window allowances, counter expiry metadata, separation of actions and
identities, keyed storage, invalid inputs and simultaneous requests from
independent database connections. The concurrency test uses a transactional
database test rather than mocked query execution.

``accounts/tests/test_registration_throttle.py`` checks HTTP throttling of
staged registration POST requests, invalid-form counting, independent IP
allowances, client-IP resolution, disabled registration, fail-closed handling,
and ``Retry-After`` responses.

``accounts/tests/test_public_resend.py`` also verifies that public resend
requires a valid rightmost forwarded IP under the production header policy
and returns HTTP 503 without a counter when that header is absent.

``accounts/tests/test_public_email_correction.py`` verifies the anonymous
CSRF-protected form, production-independent access, neutral outcomes,
credential and account-state checks, email uniqueness handling, independent
IP and username limits, token invalidation, active-job cancellation, worker
delivery, and transactional rollback on outbox failure.

``accounts/tests/test_public_request_counter_cleanup.py`` checks expiry-based
removal, bounded batches, dry-run output, empty results and invalid options
for the counter maintenance command.

``accounts/tests/test_registration_service.py`` checks atomic account and
outbox job creation, rollback on failed job reservation, uniqueness conflicts
after successful form validation, field-specific errors, rejection of invalid
forms, and propagation of unrelated database failures. The race tests use
PostgreSQL constraints, not arbitrary error-string parsing.

``accounts/tests/test_interface_translations.py`` verifies lazy account
validation labels and runtime translation of login/logout feedback and
lockout responses. The separate project-level template translation tests
are listed above.

``accounts/tests/test_login_ui.py`` checks that the dedicated sign-in
layout includes the shared fixed header, its own logo, the login form,
and the registration page link without unimplemented social sign-in.

``accounts/tests/test_views.py`` verifies the application login and logout
routes, public login page, shared layout, username/email sign-in, safe
redirects, CSRF protection, POST-only logout, and session invalidation.
It also verifies cross-page Axes lockouts, retry timing, and shared audit
events without reimplementing the existing account backend. A login-level
regression test checks the neutral error for a verification-required user
and successful login after confirmation.

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


Password recovery tests
-----------------------

``accounts/tests/test_password_reset.py`` covers the public form with
registration disabled, neutral outcomes, PostgreSQL request limits, account
eligibility, queued delivery without HTTP SMTP, duplicate/cooldown handling,
Django token confirmation, password change, invalidation of old tokens and
CSRF protection. ``accounts/tests/test_password_reset_worker.py`` covers
retry categories, exhausted attempts, expired leases, missing and inactive
accounts, account changes, safe log output, CLI validation and one-shot
operation. Tests for shared queue-command behaviour also protect the
verification worker from regressions caused by the ``EmailQueueMixin``
refactor. ``tests/test_password_reset_logging.py`` covers the extra token
redaction paths.

These automated tests use Django's test email backend and do not contact
SMTP. To test the **actual development console mailer**, run Django and the
password-reset worker in separate local processes against PostgreSQL; inspect
the resulting message in the worker terminal. See
:doc:`../getting-started/local-development`.

Run the focused password recovery tests::

   uv run pytest accounts/tests/test_password_reset.py accounts/tests/test_password_reset_worker.py tests/test_password_reset_logging.py -v --no-cov

Profile and verification flow
-----------------------------

``accounts/tests/test_email_worker.py`` tests bounded transport and unexpected
preparation/backend retries, terminal failures, safe error categories,
continuation with other jobs, and interrupt propagation, as well as lease
recovery and recipient validation. ``accounts/tests/test_email_worker_command.py``
tests the one-shot command's explicit failure and continuous polling recovery
with a minimum pause after unexpected infrastructure errors.

``accounts/tests/test_profile_verification.py`` verifies profile access,
read-only rendering, CSRF and POST-only actions, multipart delivery,
recipient selection, delivery cooldown and failure recovery, anonymous
confirmation, token invalidation, stale-address rejection, no-store and
referrer protections, and token redaction from HTTP logs. Delivery uses
Django's in-memory test mailer and does not contact the SMTP provider.

Run these integration tests with::

   uv run pytest accounts/tests/test_profile_verification.py -v --no-cov

Running tests
-------------

Start the local PostgreSQL service before running database-dependent tests::

   docker compose up -d

Run the complete test suite::

   uv run pytest

Run one test module::

   uv run pytest tests/test_settings.py

Run the staged registration configuration tests::

   uv run pytest tests/test_settings_registration.py

Run the registration page, confirmation flow and throttling tests::

   uv run pytest accounts/tests/test_registration_page.py accounts/tests/test_registration_flow.py accounts/tests/test_registration_throttle.py

Run the counter cleanup command tests::

   uv run pytest accounts/tests/test_public_request_counter_cleanup.py

Run one individual test::

   uv run pytest tests/test_settings_database.py::test_expand_database_url_without_references

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

The threshold is a minimum quality gate rather than a target. For new
security-sensitive account flows, aim for complete statement and branch
coverage, with meaningful tests of failure paths and integration boundaries.
A 90 percent configured threshold does not itself prove complete coverage.

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
