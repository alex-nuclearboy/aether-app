Environment variables
=====================

This page is the authoritative reference for environment variables consumed by
Aether and its local development tooling.

``.env.example`` is the canonical template for local development, not an
exhaustive deployment manifest. Variables that are relevant only to hosted
production environments may be documented here without being added to
``.env.example``.

Application environment
-----------------------

``AETHER_ENVIRONMENT``
   Required runtime environment classification. Supported values are
   ``development``, ``test``, and ``production``. Surrounding whitespace and
   letter case are normalised while loading the settings.

   This value is independent of ``DJANGO_DEBUG``. Production-specific safety
   validation is activated only when the value is ``production``.

Django
------

``DJANGO_SECRET_KEY``
   Required Django secret key. Generate a separate local value for development;
   production values must be supplied securely by the deployment environment.

``DJANGO_DEBUG``
   Boolean. Defaults to ``False`` in Django settings. Local development normally
   enables it. It must be ``False`` when ``AETHER_ENVIRONMENT`` is
   ``production``.

``DJANGO_ALLOWED_HOSTS``
   Comma-separated list of host names accepted by Django.

   Production requires at least one host and does not permit the unrestricted
   ``*`` wildcard.

``DJANGO_CSRF_TRUSTED_ORIGINS``
   Optional comma-separated list of additional trusted origins used for CSRF
   validation. Empty entries are discarded, surrounding whitespace is removed,
   and trailing slashes are normalised away.

``DJANGO_SECURE_SSL_REDIRECT``
   Boolean controlling Django HTTP-to-HTTPS redirection. Defaults to ``False``.

   The setting is environment-controlled but is not currently required to be
   ``True`` merely because ``AETHER_ENVIRONMENT`` is ``production``. Final
   redirect behaviour depends on the verified deployment and reverse-proxy
   configuration.

``DJANGO_SESSION_COOKIE_SECURE``
   Boolean controlling the ``Secure`` attribute of the Django session cookie.
   Defaults to ``False`` for local development and must be ``True`` in
   production.

``DJANGO_CSRF_COOKIE_SECURE``
   Boolean controlling the ``Secure`` attribute of the Django CSRF cookie.
   Defaults to ``False`` for local development and must be ``True`` in
   production.

``DJANGO_SECURE_HSTS_SECONDS``
   HTTP Strict Transport Security duration in seconds. Defaults to ``0`` and
   must not be negative.

   A positive production duration is not currently enforced. HSTS deployment
   policy will be finalised only after HTTPS behaviour has been verified.

``DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS``
   Boolean controlling whether Django adds the ``includeSubDomains`` directive
   to the HSTS header. Defaults to ``False``.

``DJANGO_SECURE_HSTS_PRELOAD``
   Boolean controlling whether Django adds the ``preload`` directive to the
   HSTS header. Defaults to ``False``.

Local PostgreSQL
----------------

``POSTGRES_DB``
   Database name used by the local PostgreSQL container. The current local
   value is ``aether``.

``POSTGRES_USER``
   PostgreSQL user created for local development. The current local value is
   ``aether``.

``POSTGRES_PASSWORD``
   Required for the local PostgreSQL container. Use a development-only value.
   Because the raw value is interpolated into ``DATABASE_URL``, manually chosen
   passwords should use ASCII letters, digits, hyphens, and underscores rather
   than URL-reserved characters.

``POSTGRES_HOST``
   Host used by Django to reach the locally published PostgreSQL port. The
   normal local value is ``127.0.0.1``.

``POSTGRES_PORT``
   Host port published by Docker Compose. The normal local value is ``5432``.

Database connection
-------------------

``DATABASE_URL``
   Required PostgreSQL connection URL used by Django. Local development can use
   ``${...}`` references to the ``POSTGRES_*`` variables; production can supply
   a complete PostgreSQL URL directly.

``DATABASE_CONN_MAX_AGE``
   Persistent database connection lifetime in seconds. Defaults to ``0``.

``DATABASE_CONN_HEALTH_CHECKS``
   Boolean controlling Django persistent-connection health checks. Defaults to
   ``False``.

``DATABASE_CONNECT_TIMEOUT``
   Maximum PostgreSQL connection-establishment time in seconds. Defaults to
   ``5`` and must be greater than zero.

Locale
------

``DJANGO_LANGUAGE_CODE``
   Django language code. Defaults to ``en-gb``.

``DJANGO_TIME_ZONE``
   Django time zone. Defaults to ``UTC``.

Logging
-------

``ROOT_LOG_LEVEL``
   Fallback logging level for otherwise unconfigured loggers. Defaults to
   ``WARNING``.

``APP_LOG_LEVEL``
   Logging level for the ``aether`` application logger. Defaults to ``DEBUG``
   when ``DJANGO_DEBUG`` is enabled and ``WARNING`` otherwise.

``DJANGO_LOG_LEVEL``
   Logging level for the Django framework. Defaults to ``INFO`` when
   ``DJANGO_DEBUG`` is enabled and ``WARNING`` otherwise.

``DATABASE_LOG_LEVEL``
   Logging level for ``django.db.backends``. Defaults to ``WARNING``. Set it to
   ``DEBUG`` only temporarily when detailed SQL logging is required.

``AUDIT_LOG_LEVEL``
   Logging level for the ``aether.audit`` logger. Defaults to ``INFO``.
