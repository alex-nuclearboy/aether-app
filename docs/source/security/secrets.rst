Secrets and sensitive configuration
===================================

Local development
-----------------

The repository commits ``.env.example`` as the local configuration template but
does not commit ``.env``. Development credentials and other local-only secrets
belong in the ignored ``.env`` file.

Generate a separate Django secret key for each local checkout. The local
``POSTGRES_PASSWORD`` is also a development-only credential and must not be
reused as a production password.

Production
----------

Production credentials must be supplied through the deployment environment and
must never be stored in the repository. The current settings allow process
environment variables to take precedence over values from a local ``.env``
file.

When Koyeb and Neon deployment is implemented, this page will document the
actual secret-management path used by those services.

Continuous integration
----------------------

GitHub Actions uses disposable CI-only values for the Django secret key and
PostgreSQL credentials. They protect only the ephemeral CI environment and are
not production secrets.

Real provider credentials, OAuth client secrets, API keys, and production
database credentials must not be embedded in workflow files.

Logging
-------

Sensitive configuration must not be written to application logs.

This includes:

* passwords;
* Django secret keys;
* database credentials;
* API keys;
* OAuth access and refresh tokens;
* session identifiers;
* CSRF tokens;
* sensitive submitted form contents.

The same rule applies to development ``DEBUG`` logging. Increased verbosity
must never expose secret values.

Local development log files are stored under ``logs/`` and are excluded from
version control.
