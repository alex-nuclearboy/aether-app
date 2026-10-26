Project structure
=================

Aether is still at an early stage, so the repository is intentionally small.
The current structure contains the Django project configuration, local
development infrastructure, automated tests, documentation, and code-quality
tooling.

Application-specific Django apps, integrations, and service layers are added as
the corresponding functionality is implemented rather than being created in
advance.

The ``accounts`` application manages user accounts and authentication, while
the ``core`` application provides the initial public home page.

Tests that belong to application components are introduced together with the
code they verify.

Current structure
-----------------

The repository currently has the following top-level structure:

.. code-block:: text

   aether-app/
   ├── .github/
   │   └── workflows/
   │       └── code-quality.yml
   ├── accounts/
   │   ├── migrations/
   │   │   ├── __init__.py
   │   │   ├── 0001_initial.py
   │   │   └── ...
   │   ├── tests/
   │   │   ├── __init__.py
   │   │   ├── test_admin.py
   │   │   ├── test_audit.py
   │   │   ├── test_backends.py
   │   │   ├── test_forms.py
   │   │   ├── test_lockout_responses.py
   │   │   ├── test_lockouts.py
   │   │   ├── test_login_ui.py
   │   │   ├── test_models.py
   │   │   ├── test_validators.py
   │   │   └── test_views.py
   │   ├── templates/
   │   │   └── accounts/
   │   │       └── login.html
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── audit.py
   │   ├── backends.py
   │   ├── forms.py
   │   ├── lockout_responses.py
   │   ├── lockouts.py
   │   ├── models.py
   │   ├── urls.py
   │   ├── validators.py
   │   └── views.py
   ├── config/
   │   ├── __init__.py
   │   ├── asgi.py
   │   ├── logging.py
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   ├── core/
   │   ├── migrations/
   │   │   └── __init__.py
   │   ├── templates/
   │   │   └── core/
   │   │       └── home.html
   │   ├── tests/
   │   │   ├── __init__.py
   │   │   └── test_views.py
   │   ├── __init__.py
   │   ├── admin.py
   │   ├── apps.py
   │   ├── models.py
   │   ├── urls.py
   │   └── views.py
   ├── docs/
   │   ├── source/
   │   │   ├── architecture/
   │   │   ├── deployment/
   │   │   ├── development/
   │   │   ├── getting-started/
   │   │   ├── integrations/
   │   │   ├── reference/
   │   │   ├── security/
   │   │   ├── conf.py
   │   │   └── index.rst
   │   ├── Makefile
   │   ├── make.bat
   │   └── README.md
   ├── infrastructure/
   │   ├── __init__.py
   │   ├── request.py
   │   └── request_id.py
   ├── static/
   │   ├── css/
   │   │   ├── foundations/
   │   │   │   └── tokens.css
   │   │   ├── components/
   │   │   │   ├── alert.css
   │   │   │   ├── button.css
   │   │   │   ├── form-field.css
   │   │   │   └── header.css
   │   │   ├── pages/
   │   │   │   ├── home.css
   │   │   │   └── login.css
   │   │   ├── base.css
   │   │   └── layout.css
   │   ├── favicons/
   │   └── images/
   │       ├── aether_logo.png
   │       └── aether_logo_full.png
   ├── templates/
   │   ├── components/
   │   │   ├── form_field.html
   │   │   └── messages.html
   │   ├── includes/
   │   │   └── header.html
   │   └── base.html
   ├── tests/
   │   ├── __init__.py
   │   ├── test_authentication_settings.py
   │   ├── test_database.py
   │   ├── test_django_entrypoints.py
   │   ├── test_frontend.py
   │   ├── test_logging.py
   │   ├── test_messages.py
   │   ├── test_request.py
   │   ├── test_request_id.py
   │   └── test_settings.py
   ├── .env.example
   ├── .gitignore
   ├── .python-version
   ├── compose.yaml
   ├── LICENSE
   ├── manage.py
   ├── pyproject.toml
   ├── README.md
   └── uv.lock


Accounts application
--------------------

``accounts/``
~~~~~~~~~~~~~

The ``accounts`` package contains Aether's project-specific user-account
functionality.

The application currently defines a custom Django user model based on
``AbstractUser``. Keeping a project-owned user model from the beginning allows
account-specific fields and authentication behaviour to evolve without
replacing Django's built-in user model later.

The current user model retains ``username`` as Django's primary user identifier.
Usernames are limited to 3--32 ASCII characters and may contain letters,
digits, periods, underscores, and hyphens. They must start and end with a
letter or digit.

Username and email uniqueness are both enforced case-insensitively at the
database level while their stored values are not forcibly converted entirely
to lowercase. Email addresses continue to use Django's standard email-field
validation.

The authentication backend accepts either a username or an email address,
with case-insensitive matching. It inherits Django's standard password
hash verification, active-user checks, and group/permission handling.

Django groups and permissions remain available through ``AbstractUser`` and
will be used when application access rules are introduced. No project-specific
roles or access levels are defined at this stage.

``accounts/models.py``
~~~~~~~~~~~~~~~~~~~~~~

Defines the project-specific ``User`` model and the database constraints that
protect account identifiers.

The model retains ``username`` as Django's ``USERNAME_FIELD`` while enforcing
the project-specific username length and syntax rules. Functional unique
constraints prevent usernames and email addresses that differ only by letter
case from representing separate accounts.

``accounts/backends.py``
~~~~~~~~~~~~~~~~~~~~~~~~

Defines ``UsernameOrEmailBackend``, a subclass of Django's
``ModelBackend``.

The backend selects the username or email lookup according to the
presence of ``@`` in the submitted identifier. Both lookups are
case-insensitive.

Synchronous and asynchronous authentication use Django's password
verification and timing-attack mitigation mechanisms. The backend
also preserves Django's inactive-user checks and permission system.

The module also defines ``AsyncAxesStandaloneBackend``, which provides
asynchronous compatibility for the django-axes lockout checks.

``accounts/lockouts.py``
~~~~~~~~~~~~~~~~~~~~~~~~

Provides the account identifier normalisation function used by django-axes.

Known usernames and email addresses are resolved to the same
case-normalised username. Unknown identifiers are normalised without
creating or modifying user accounts.

This enables a shared failure counter for both authentication identifiers
of the same account.

The module also provides ``get_lockout_deadline`` and
``get_lockout_remaining_seconds``. These helpers use the django-axes database
records, resolved client IP address, and configured cool-off period to
calculate the deadline of an active lockout and the remaining seconds.
They support audit reporting and future authentication interfaces without
reading log messages.

``accounts/validators.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines reusable validation rules for account identifiers.

The current username validator accepts 3--32 ASCII characters using letters,
digits, periods, underscores, and hyphens, with an alphanumeric first and last
character.

``accounts/admin.py``
~~~~~~~~~~~~~~~~~~~~~

Registers the custom user model with Django administration and extends the
standard user administration configuration so the required email address is
available when accounts are created.

``accounts/apps.py``
~~~~~~~~~~~~~~~~~~~~

Defines the Django application configuration for the accounts package.

The ``ready()`` method registers the authentication audit signal receivers
during application initialisation.

``accounts/audit.py``
~~~~~~~~~~~~~~~~~~~~~

Defines Django signal receivers for successful login, failed login,
authenticated logout, and newly triggered authentication lockouts.

The receivers write structured messages to ``aether.audit``. All events
include a keyed SHA-256 HMAC fingerprint of the canonical login identifier
and the resolved client IP address. Successful login and authenticated
logout events also include the verified ``user_id``.

Failed authentication and lockout events do not include a user ID.
New lockout events additionally record the failure count, configured
duration, remaining-time snapshot, and UTC deadline.

Plaintext usernames, email addresses, and credentials are excluded from
custom authentication audit events. Anonymous logout signals are ignored.
Repeated blocked POST requests are audited separately through
``accounts/lockout_responses.py``.

``accounts/lockout_responses.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implements the response callable used by django-axes for HTTP 429. It provides
an up-to-date ``Retry-After`` header and prevents caching. It records a
``authentication.lockout_denied`` audit event for repeated blocked POSTs,
without creating an additional database model or extending the deadline.

``accounts/forms.py``
~~~~~~~~~~~~~~~~~~~~~

Defines ``AetherAuthenticationForm``, extending Django's standard
``AuthenticationForm`` with a username-or-email label and neutral errors.
Password verification remains in the existing authentication backend.

``accounts/views.py``
~~~~~~~~~~~~~~~~~~~~~

Defines ``AetherLoginView`` and ``AetherLogoutView``, extending Django's
standard session login and logout views.

The login view uses ``AetherAuthenticationForm`` and the application login
template. Both views create one-time success messages after successful
sign-in or sign-out.

``accounts/urls.py``
~~~~~~~~~~~~~~~~~~~~

Registers application login at ``/login/`` and POST-only session logout at
``/logout/``. The project URL configuration includes these routes while
keeping Django Admin authentication independent.

``accounts/templates/accounts/login.html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides the sign-in form, Django CSRF token, neutral validation messages,
and a safe ``next`` field. It extends the shared Aether base template.

``accounts/migrations/``
~~~~~~~~~~~~~~~~~~~~~~~~

Contains database migrations for the accounts application. The custom user
model is introduced in ``0001_initial.py``, while later migrations evolve the
account identifier rules and database constraints.

``accounts/tests/``
~~~~~~~~~~~~~~~~~~~

Contains automated tests specific to the accounts application, including:

* user model behaviour and database constraints;
* Django administration integration;
* account identifier validation and case-insensitive uniqueness;
* username-or-email authentication with case-insensitive lookups;
* password verification, inactive-user rejection, and timing-attack mitigation;
* synchronous and asynchronous authentication;
* inherited Django group and permission handling;
* authentication lockout thresholds and identifier normalisation;
* lockout expiration, counter resets, and account/IP isolation;
* asynchronous lockout enforcement;
* lockout deadline calculation, remaining time, and expiry;
* successful and failed login, logout, and lockout audit events, including
  sensitive-data handling and separate repeat-denial events;
* HTTP 429 response headers and recalculated lockout wait times;
* application login form, CSRF, safe redirects, and POST-only logout;
* shared session, Axes, and audit behaviour across Admin and application.


Core application
----------------

``core/``
~~~~~~~~~

The ``core`` application provides general-purpose pages that do not belong to
a specific application domain.

The current implementation exposes a public home page at ``/``. The page
displays the full Aether logo within the shared application layout.

A fixed header links the compact Aether brand to the home page and
provides sign-in or sign-out controls depending on authentication status.
A sidebar and additional navigation menus are not implemented.

``core/apps.py``
~~~~~~~~~~~~~~~~

Defines the Django application configuration through ``CoreConfig``.

``core/views.py``
~~~~~~~~~~~~~~~~~

Defines the ``home`` view, which renders the public home page.

``core/urls.py``
~~~~~~~~~~~~~~~~

Defines the ``home`` URL pattern for the root path ``/``.

``core/templates/core/home.html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the home page template, which extends the shared base layout,
loads its own stylesheet, and displays the full Aether logo as the page heading.

``core/admin.py``
~~~~~~~~~~~~~~~~~

Reserved for future Django administration registrations.

``core/models.py``
~~~~~~~~~~~~~~~~~~

Reserved for future core application models. No database models are currently
defined by this application.

``core/migrations/``
~~~~~~~~~~~~~~~~~~~~~

Contains the Django migrations package. No core database migrations are
currently required.

``core/tests/``
~~~~~~~~~~~~~~~

Contains application-specific tests for home page routing, anonymous
access, template inheritance, the header's home link, and discovery of
stylesheets, logos, and favicon assets.


Shared interface resources
--------------------------

``templates/base.html``
~~~~~~~~~~~~~~~~~~~~~~~

Defines the shared HTML document, favicon links, and stylesheet load order.
Shared stylesheets load before the page-specific ``page_styles`` block.

The template includes the fixed site header on every page, renders
one-time Django messages, and provides the main content block.

``templates/includes/header.html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides the common site header and session-aware account navigation. The
sign-in link and POST-only sign-out button reuse the shared button styles.

``templates/components/form_field.html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides reusable Django form-field labels, widgets and validation messages.
Application templates include this partial rather than repeating its markup.

``templates/components/messages.html``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Renders one-time Django notifications using the shared semantic alert
component. Messages are displayed before the page-specific content.

``static/css/foundations/tokens.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Contains the light-only primitive and semantic colour palette, spacing,
typography, control sizing and the mobile-first responsive viewport rules.

``static/css/base.css``
~~~~~~~~~~~~~~~~~~~~~~~

Contains document defaults, box sizing and common keyboard focus indicators.

``static/css/layout.css``
~~~~~~~~~~~~~~~~~~~~~~~~~

Controls shared maximum content width and responsive page gutters.

``static/css/components/alert.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines shared success, error, warning, and informational alerts,
including compact validation feedback for authentication forms.

``static/css/components/button.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines reusable primary and quiet button variants, including links styled
as buttons.

``static/css/components/form-field.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines shared label, widget and validation styles used by Django forms.

``static/css/components/header.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the fixed header layout and site branding, using responsive tokens.

``static/css/pages/home.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Centres the Aether logo in the available home page content area.

``static/css/pages/login.css``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the login-page layout, branding, title, panel, form spacing,
and submit button width. Shared components provide the form controls,
buttons, and validation feedback.

For the component and viewport rules, see :doc:`../development/frontend`.

``static/images/``
~~~~~~~~~~~~~~~~~~~

Contains ``aether_logo.png``, used in the shared header and login page,
and ``aether_logo_full.png``, displayed on the home page.

``static/favicons/``
~~~~~~~~~~~~~~~~~~~~

Contains browser favicons, the Apple touch icon, and the web application
manifest. These assets are referenced from the shared base template.

The interface currently loads Inter through Google Fonts. It has no footer or
responsive sidebar layout implementation at this stage.


Django project configuration
----------------------------

``config/``
~~~~~~~~~~~

The ``config`` package contains the project-level Django configuration.

It is responsible for settings, root URL routing, and the WSGI and ASGI
application entry points. Application-specific code should not normally be
placed here.

``config/settings.py``
~~~~~~~~~~~~~~~~~~~~~~

The main Django settings module.

The file currently handles:

* environment-variable loading;
* explicit runtime environment classification;
* validation of required and production-sensitive configuration;
* Django security settings;
* environment-specific client IP resolution and proxy policy;
* installed applications and middleware;
* the project-specific Django user model;
* authentication lockout protection through django-axes;
* PostgreSQL configuration;
* database connection settings;
* logging level selection and logging configuration integration;
* password validation;
* internationalisation;
* shared template discovery and static file configuration;
* email backend configuration.

Configuration is environment-driven. Local development values are loaded from
``.env``, while deployment environments can provide their own environment
variables.

Email configuration follows the same boundary. Development and test
environments use Django's console backend, while production uses a
provider-neutral SMTP configuration. Mailjet-specific details are kept in
:doc:`../integrations/mailjet`.

Database URLs are validated before being converted into Django database
settings. Aether currently requires PostgreSQL rather than supporting multiple
database backends.

For a detailed explanation of the configuration model, see
:doc:`configuration`.

For the complete environment-variable reference, see
:doc:`../reference/environment-variables`.

``config/logging.py``
~~~~~~~~~~~~~~~~~~~~~

Contains the project logging configuration.

The module is responsible for:

* validating configured log levels;
* defining plain and coloured formatters;
* configuring console logging;
* configuring rotating development log files;
* separating development and production handlers;
* defining the ``aether``, Django, database, and audit logger groups;
* attaching request correlation IDs to log records through a shared
  logging filter.

Development console output uses ``colorlog``. Local development also writes
plain-text logs to ``logs/aether.log`` with rotation.

Production does not configure a file handler and writes logs only to the
console.

See :doc:`../development/logging` for the detailed logging policy.

``config/urls.py``
~~~~~~~~~~~~~~~~~~

Defines the root URL configuration for the Django project.

The root URL configuration exposes the Django administration interface at
``/admin/`` and includes the ``core`` application routes at ``/``.

Additional application-specific routes will be introduced as their
corresponding functionality is implemented.

``config/asgi.py``
~~~~~~~~~~~~~~~~~~

Exposes the ASGI application used by ASGI-compatible application servers.

Keeping the ASGI entry point available allows the deployment architecture to
support asynchronous Django capabilities if they are required later.

``config/wsgi.py``
~~~~~~~~~~~~~~~~~~

Exposes the WSGI application used by WSGI-compatible application servers.

The final production server configuration will be documented together with
the Koyeb deployment setup once deployment is introduced.

``config/__init__.py``
~~~~~~~~~~~~~~~~~~~~~~

Marks ``config`` as a Python package.

It intentionally contains no project configuration.


Shared infrastructure
---------------------

``infrastructure/``
~~~~~~~~~~~~~~~~~~~

Contains reusable infrastructure utilities shared across Django applications
and project-level components.

It is a regular Python package and is not included in ``INSTALLED_APPS``.

``infrastructure/request_id.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides server-generated HTTP request correlation IDs. Hybrid middleware
supports sync and async requests, stores the active ID in a ``ContextVar``,
and returns it through the ``X-Request-ID`` response header. A logging filter
adds the request ID to console and file log records. The middleware also
records HTTP responses through ``aether.http`` before the request context is
cleared, using ``INFO`` for ordinary responses, ``WARNING`` for HTTP 429, and
``ERROR`` for HTTP 5xx.

``infrastructure/request.py``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides shared HTTP request utilities for resolving and normalising client
IP addresses.

``_normalise_ip()`` validates and canonicalises IPv4 and IPv6 addresses,
including IPv4-mapped IPv6 addresses. Invalid addresses return ``None``.

``get_client_ip()`` resolves addresses according to the runtime environment.

Development and test environments use ``django-ipware`` with
``REMOTE_ADDR`` as the only permitted address source. Production explicitly
selects the last ``X-Forwarded-For`` address, falling back to
``REMOTE_ADDR`` when the header is absent.

The production selection does not use the django-ipware
``CLIENT_IP_PROXY_ORDER`` setting. See :doc:`../security/django`
for the proxy trust policy and deployment requirements.

The shared resolver is used by django-axes for authentication lockout
protection and by the authentication audit handlers for client IP logging.


Project entry point
-------------------

``manage.py``
~~~~~~~~~~~~~

The command-line entry point for Django administrative tasks.

Common commands include:

.. code-block:: console

   uv run python manage.py check
   uv run python manage.py makemigrations
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   uv run python manage.py runserver

The full command reference is available in
:doc:`../reference/commands`.


Dependency and Python configuration
-----------------------------------

``pyproject.toml``
~~~~~~~~~~~~~~~~~~

Defines the Python project metadata and dependency configuration used by
``uv``.

It contains:

* project metadata;
* supported Python versions;
* runtime dependencies;
* development dependencies;
* ``uv`` configuration;
* pytest and coverage configuration;
* Pylint configuration.

Runtime dependencies are packages required by the application itself.
Development-only tools such as pytest, pytest-django, pytest-cov, Pylint, and
Sphinx belong to the development dependency group.

``colorlog`` is a runtime dependency because the logging configuration provides
colour-aware development console formatting.

``uv.lock``
~~~~~~~~~~~

The lock file generated and maintained by ``uv``.

It records the exact resolved dependency graph so that local development and
continuous integration use reproducible package versions.

The file is committed to the repository and should normally be updated through
``uv`` rather than edited manually.

``.python-version``
~~~~~~~~~~~~~~~~~~~

Defines the preferred Python version for local development.

The project may support more than one Python version, while this file provides
a consistent default for developers and tooling that understand
``.python-version`` files.

The primary CI quality job also uses this preferred version. Other supported
Python versions are verified separately by the compatibility matrix rather
than changing the project's local version pin.


Environment configuration
-------------------------

``.env.example``
~~~~~~~~~~~~~~~~

Provides the version-controlled template for the local development
environment.

It contains safe local defaults and placeholders for secrets that must be
configured after the file is copied to ``.env``. It must never contain real
development or production credentials.

The file is intentionally scoped to local development and is not an exhaustive
catalogue of every environment variable supported by Aether. Production-only
and deployment-specific configuration is documented separately.

The current template includes configuration for:

* runtime environment classification;
* local Django and security settings;
* the local default email sender;
* the local PostgreSQL instance;
* ``DATABASE_URL`` and database connection behaviour;
* application language and time zone;
* logging levels.

The complete application environment-variable reference is maintained in
:doc:`../reference/environment-variables`.

``.env``
~~~~~~~~

The local environment file.

It is created from ``.env.example`` during local setup and is intentionally
excluded from version control because it may contain credentials and other
machine-specific values.

Production environments do not rely on the repository's local ``.env`` file.
Deployment configuration and secrets are supplied through the hosting
environment instead.


Local PostgreSQL infrastructure
-------------------------------

``compose.yaml``
~~~~~~~~~~~~~~~~

Defines the Docker Compose service used for the local PostgreSQL database.

The configuration currently provides:

* PostgreSQL 18;
* environment-based database name, user, and password;
* a host-only PostgreSQL port binding;
* persistent storage through a named Docker volume;
* a PostgreSQL health check.

Docker Compose is part of the local development environment only. The planned
production environment uses managed PostgreSQL instead.

See :doc:`../development/database` for the local database workflow and
:doc:`../deployment/index` for the current production direction.

Testing
-------

``tests/``
~~~~~~~~~~

Contains project-level automated tests for configuration, infrastructure, and
Django project entry points.

The current package contains:

``tests/test_settings.py``
   Tests runtime environment handling, Django security configuration,
   production safety validation, PostgreSQL configuration, database URL
   expansion, connection options, logging overrides, email backend selection,
   production SMTP validation, and module-level settings behaviour.

``tests/test_database.py``
   Contains integration tests that verify PostgreSQL as the configured database
   backend and execute queries through Django's database connection.

``tests/test_django_entrypoints.py``
   Contains smoke tests for the ASGI application, WSGI application, and root
   URL configuration.

``tests/test_logging.py``
   Tests logging-level validation, development and production handlers,
   colour formatting, local file rotation, logger levels, propagation,
   and request ID filter configuration.

``tests/test_frontend.py``
   Tests shared form-field markup, reusable CSS files, breakpoint declarations,
   and base-template stylesheet inclusion.

``tests/test_request_id.py``
   Verifies request ID generation, uniqueness, context isolation and cleanup,
   synchronous and asynchronous middleware, HTTP response logging levels,
   and authentication audit correlation.

``tests/test_request.py``
   Tests shared IP address normalisation, client IP resolution in development
   and production, forwarding-header handling, and proxy-policy integration.

``tests/__init__.py``
   Marks the root test directory as a Python package.

The root ``tests/`` package is intended for project-wide configuration and
infrastructure tests. Tests that belong to a specific Django application should
normally live inside that application's own ``tests/`` package.

Aether uses ``pytest`` and ``pytest-django`` for test execution and
``pytest-cov`` for statement and branch coverage.

See :doc:`../development/testing` for the testing strategy, PostgreSQL test
database behaviour, coverage policy, and supported test commands.

Continuous integration
----------------------

``.github/workflows/code-quality.yml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the GitHub Actions workflow used for automated project validation.

The workflow has four distinct responsibilities:

``quality``
   Runs the complete project checks using the preferred Python version from
   ``.python-version``. It validates the lock file and installed dependencies,
   starts PostgreSQL, runs Django checks, checks static file collection in
   dry-run mode, applies migrations, executes the automated tests with coverage,
   runs Pylint, and builds the Sphinx documentation.

``python-compatibility``
   Runs the dependency, Django, migration, and test checks on Python 3.12 and
   3.13. Python 3.14 is not duplicated in this matrix because it is already
   exercised by the primary ``quality`` job.

``deployment-checks``
   Runs Django's deployment checks using a synthetic production-shaped
   configuration. It exercises the ``AETHER_ENVIRONMENT=production`` settings
   path without using real production credentials or defining the final Koyeb
   deployment policy.

``security``
   Audits the locked dependency graph for Python 3.12, 3.13, and 3.14 on Linux
   using ``uv audit``.

The test-oriented jobs share the same disposable Django environment and
PostgreSQL 18 service configuration. YAML anchors are used inside the workflow
to keep these shared definitions in one place.

The security job is independent of Django and PostgreSQL because dependency
auditing operates directly on the locked dependency graph.

See :doc:`../development/continuous-integration` for the detailed workflow and
:doc:`../security/dependencies` for dependency-security policy.


Documentation
-------------

``docs/``
~~~~~~~~~

Contains the Sphinx documentation project.

The documentation is intentionally separated from the root ``README.md``.
The README provides a concise project introduction and quick-start workflow,
while Sphinx contains the detailed development, architecture, deployment,
security, and reference documentation.

The directory contains:

.. code-block:: text

   docs/
   ├── source/
   │   ├── architecture/
   │   ├── deployment/
   │   ├── development/
   │   ├── getting-started/
   │   ├── integrations/
   │   ├── reference/
   │   ├── security/
   │   ├── conf.py
   │   └── index.rst
   ├── Makefile
   ├── make.bat
   └── README.md

``docs/source/``
~~~~~~~~~~~~~~~~

Contains the documentation source files.

The documentation is organised by purpose rather than by Python package:

``getting-started/``
   Initial setup and local development onboarding.

``development/``
   Development workflows such as PostgreSQL, automated testing, logging, code
   quality, continuous integration, and documentation maintenance.

``architecture/``
   Explanations of the project structure, configuration model, and architectural
   decisions.

``deployment/``
   Production deployment documentation. This section will expand when the
   Koyeb and Neon environments are implemented.

``integrations/``
   Documentation for provider-specific external-service integrations. The
   section currently documents Mailjet as the selected production email
   provider and will expand as additional integrations such as Google Calendar,
   external APIs, and cloud-backed file storage are introduced.

``security/``
   Security-related documentation covering Django security configuration,
   username-or-email authentication, brute-force protection, secret handling,
   dependency security, and future OAuth concerns.

``reference/``
   Precise technical reference material such as environment variables and
   commonly used commands.

``docs/source/conf.py``
~~~~~~~~~~~~~~~~~~~~~~~

Contains the Sphinx configuration.

It defines the documentation project metadata and build configuration. The
project version is read from ``pyproject.toml`` so that it does not need to be
duplicated manually in the documentation configuration.

The file is included in the project's Pylint checks.

``docs/source/index.rst``
~~~~~~~~~~~~~~~~~~~~~~~~~

The root page of the Sphinx documentation.

It defines the top-level documentation navigation and links the main
documentation sections together.

``docs/Makefile`` and ``docs/make.bat``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convenience build helpers generated for the Sphinx documentation.

The documentation can also be built directly with ``sphinx-build``. See
:doc:`../development/documentation` for the supported build commands.

``docs/_build/``
~~~~~~~~~~~~~~~~

Contains generated Sphinx output.

This directory is generated locally or in CI and is excluded from version
control.


Repository documentation
------------------------

``README.md``
~~~~~~~~~~~~~

The main entry point for the repository.

It provides:

* a concise description of Aether;
* local requirements;
* the quick-start workflow;
* essential development and test commands;
* documentation build instructions;
* the current deployment direction.

Detailed technical explanations belong in the Sphinx documentation rather than
being duplicated in the README.

``LICENSE``
~~~~~~~~~~~

Contains the GNU Affero General Public License version 3 under which Aether is
distributed.


Version-control configuration
-----------------------------

``.gitignore``
~~~~~~~~~~~~~~

Defines files and directories that must not be committed.

This includes local environments, generated Python files, local credentials,
database artefacts, documentation build output, and development-tool caches.


Generated and local-only files
------------------------------

Several files and directories may exist in a local checkout without appearing
in the repository.

Important examples include:

``.env``
   Local environment configuration and credentials.

``.venv/``
   The local Python virtual environment managed by ``uv``.

``docs/_build/``
   Generated Sphinx documentation.

``.pytest_cache/``
   Local pytest cache generated during test execution.

``__pycache__/``
   Generated Python bytecode cache directories.

``.coverage``
   Local coverage data generated while running the automated test suite.

``logs/``
   Local development logs generated by the rotating file handler. The directory
   contains ``aether.log`` and any rotated backups and is excluded from version
   control.

Docker volumes
   Persistent PostgreSQL data managed by Docker rather than stored inside the
   repository.

These artefacts are deliberately kept outside version control.


Future growth
-------------

The current structure should expand only when corresponding functionality is
introduced.

Expected areas include Django applications for the product domain, service
layers, external integrations, and provider-specific infrastructure.
Application-specific test packages should be introduced alongside the
components they verify.

The final package structure should be driven by implementation needs rather
than by creating placeholder modules in advance.

The architecture documentation should be updated whenever a structural change
introduces a new long-lived project component.
