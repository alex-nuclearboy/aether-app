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

Validation
----------

Required and security-sensitive values fail early when configuration is missing
or invalid. The current settings validate:

* ``DJANGO_SECRET_KEY``;
* ``DATABASE_URL``;
* the PostgreSQL URL scheme and required connection components;
* non-negative database connection lifetime;
* positive database connection timeout.

Database URL references
-----------------------

For local development, ``DATABASE_URL`` can contain braced references such as
``${POSTGRES_USER}``. The project expands these references from environment
variables before the URL is parsed by ``django-environ``.

This lets Docker Compose and Django share the same local database values without
repeating the credentials in multiple settings.

Production configuration
------------------------

Production is expected to supply a complete PostgreSQL connection URL and other
settings through the deployment environment. The exact Koyeb and Neon
configuration will be documented only after the production deployment is
implemented and verified.

See :doc:`../reference/environment-variables` for the current variable
reference.
