Environment variables
=====================

``.env.example`` is the canonical template for local development. The entries
below summarise the variables currently used by Django or Docker Compose.

Django
------

``DJANGO_SECRET_KEY``
   Required. Django secret key. Generate a local value for development;
   production values must be supplied securely by the deployment environment.

``DJANGO_DEBUG``
   Boolean. Defaults to ``False`` in Django settings. The local environment can
   enable it for development.

``DJANGO_ALLOWED_HOSTS``
   Comma-separated list of host names accepted by Django.

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
