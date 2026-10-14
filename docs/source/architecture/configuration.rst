Configuration model
===================

Aether uses environment-driven configuration so the same Django settings module
can serve local development and deployment environments.

Configuration sources
---------------------

Local development uses a repository-root ``.env`` file created from
``.env.example``. The local file is ignored by Git.

Deployment environments are expected to provide settings through process
environment variables. Existing process variables take precedence over values
loaded from ``.env``. This allows the same settings code to run locally and on
the deployment platform without a separate production settings module.

``.env.example`` is intentionally scoped to local development. It is not an
exhaustive manifest of every environment variable that may be used by a
deployment.

The complete application configuration contract is documented in
:doc:`../reference/environment-variables`. Deployment-platform mappings,
provider-specific values, and production secret storage belong in the
corresponding deployment or integration documentation.

Runtime environment classification
----------------------------------

Aether identifies the runtime environment explicitly through
``AETHER_ENVIRONMENT``.

The supported values are:

* ``development``;
* ``test``;
* ``production``.

Runtime environment classification is deliberately independent of
``DJANGO_DEBUG``. Disabling Django debug mode does not by itself mean that the
application is running in production; for example, CI may run with
``DJANGO_DEBUG=False`` while remaining a test environment.

The environment value is required and is normalised by trimming surrounding
whitespace and converting it to lowercase. Missing or unsupported values cause
configuration to fail during settings loading.

Validation
----------

Required and security-sensitive values fail early when configuration is missing
or invalid. The current settings validate:

* ``AETHER_ENVIRONMENT`` and its supported values;
* ``DJANGO_SECRET_KEY``;
* production debug mode;
* production allowed-host configuration;
* production session and CSRF cookie security;
* non-negative HSTS duration;
* ``DATABASE_URL``;
* the PostgreSQL URL scheme and required connection components;
* non-negative database connection lifetime;
* positive database connection timeout;
* configured logging levels.

When ``AETHER_ENVIRONMENT`` is ``production``, Aether additionally requires:

* ``DJANGO_DEBUG=False``;
* at least one configured allowed host;
* no wildcard ``*`` in ``DJANGO_ALLOWED_HOSTS``;
* secure session cookies;
* secure CSRF cookies.

These checks express application-level production invariants without deriving
the runtime environment from ``DJANGO_DEBUG``.

Django security configuration
-----------------------------

HTTPS redirection, secure-cookie behaviour, trusted CSRF origins, and HSTS
settings are configurable through environment variables.

Some deployment-specific decisions are deliberately not enforced yet.
``SECURE_SSL_REDIRECT`` is configurable but is not currently a production
invariant, and ``SECURE_PROXY_SSL_HEADER`` is not configured until the
behaviour of the production reverse proxy has been verified.

HSTS can also be configured through the environment. The settings currently
reject a negative duration but do not require HSTS to be enabled in production.
The final HTTPS, proxy, and HSTS policy will be completed alongside the verified
deployment configuration.

See :doc:`../security/django` for the detailed Django security model.

Database URL references
-----------------------

For local development, ``DATABASE_URL`` can contain braced references such as
``${POSTGRES_USER}``. The project expands these references from environment
variables before the URL is parsed by ``django-environ``.

This lets Docker Compose and Django share the same local database values without
repeating the credentials in multiple settings.

Logging configuration
---------------------

Logging configuration is separated from the main Django settings module.

``config/settings.py`` reads the environment-specific logging levels and passes
them to ``config/logging.py``. The logging module validates those values and
builds the final Django ``LOGGING`` dictionary.

This separation keeps formatter, handler, rotation, and logger definitions out
of the main settings module while still allowing environment-specific defaults
and overrides.

Development uses coloured console output and a rotating local log file.
Production uses plain console logging only.

See :doc:`../development/logging` for the complete logging behaviour.

Production configuration
------------------------

Production is expected to supply a complete PostgreSQL connection URL and other
settings through the deployment environment. The exact Koyeb and Neon
configuration will be documented only after the production deployment is
implemented and verified.

See :doc:`../reference/environment-variables` for the current variable
reference.
