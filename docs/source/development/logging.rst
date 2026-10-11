Logging
=======

Aether uses Python and Django logging with a project-specific configuration
defined in ``config/logging.py``.

The configuration is designed to provide detailed but controlled output during
local development while keeping production logging concise and suitable for a
container-based deployment environment.


Logging environments
--------------------

Development and production use different logging behaviour.

During local development:

* console output uses coloured log levels;
* application logging defaults to ``DEBUG``;
* Django logging defaults to ``INFO``;
* database query logging defaults to ``WARNING``;
* audit logging defaults to ``INFO``;
* logs are also written to a rotating local file.

In production:

* console output uses a plain formatter;
* application logging defaults to ``WARNING``;
* Django logging defaults to ``WARNING``;
* database query logging defaults to ``WARNING``;
* audit logging defaults to ``INFO``;
* no log files are written inside the application container.

Production logs are therefore intended for standard output and standard error,
where they can be collected by the hosting platform.


Logger groups
-------------

The current configuration defines the following logger groups.

``root``
   Fallback logger for libraries and code without a more specific logger.
   Its default level is ``WARNING``.

``aether``
   Main logger namespace for Aether application code. It defaults to
   ``DEBUG`` during development and ``WARNING`` in production.

``django``
   Django framework logging. It defaults to ``INFO`` during development and
   ``WARNING`` in production.

``django.db.backends``
   Django database query logging. It defaults to ``WARNING`` in all
   environments.

``aether.audit``
   Reserved for security-relevant and audit events. It defaults to ``INFO`` in
   all environments.

The audit logger is part of the logging foundation, but audit events should be
added only when corresponding application behaviour such as authentication,
access control, integrations, or automation is implemented.


Log levels
----------

The following levels are supported:

* ``DEBUG``;
* ``INFO``;
* ``WARNING``;
* ``ERROR``;
* ``CRITICAL``.

Configured values are normalised to uppercase and validated during Django
settings loading. Unsupported values cause an ``ImproperlyConfigured`` error
rather than being silently accepted.


Environment overrides
---------------------

Logging levels can be overridden independently through environment variables:

* ``ROOT_LOG_LEVEL``;
* ``APP_LOG_LEVEL``;
* ``DJANGO_LOG_LEVEL``;
* ``DATABASE_LOG_LEVEL``;
* ``AUDIT_LOG_LEVEL``.

This allows temporary changes without modifying application code.

For example, SQL logging can be enabled locally by setting::

   DATABASE_LOG_LEVEL=DEBUG

Database ``DEBUG`` logging should be used only when investigating queries.
Leaving it enabled during normal development produces a large amount of output
and may expose query parameters in logs.


Coloured development output
----------------------------

Development console output uses ``colorlog``.

The current level colours are:

* ``DEBUG`` — cyan;
* ``INFO`` — green;
* ``WARNING`` — yellow;
* ``ERROR`` — red;
* ``CRITICAL`` — bold red.

Colour formatting is used only for the development console. File logging and
production console logging use a plain text formatter.


Local log files
---------------

When Django runs with ``DEBUG=True``, logging also writes to::

   logs/aether.log

The file uses ``RotatingFileHandler`` with:

* a maximum active file size of 5 MiB;
* three retained backup files;
* UTF-8 encoding.

The total maximum local storage is therefore approximately 20 MiB across the
active file and three backups.

The ``logs/`` directory is local-only and must remain excluded from version
control.


Production logging
------------------

When ``DEBUG=False``, the file handler is not configured.

Production logging is written only to the console using the plain formatter.
This avoids storing logs inside an ephemeral application container and allows
the deployment platform to collect them directly.


Sensitive data
--------------

Logs must never contain:

* passwords;
* Django secret keys;
* database passwords or complete credential-bearing database URLs;
* API keys;
* OAuth access or refresh tokens;
* session identifiers;
* CSRF tokens;
* submitted form contents containing sensitive data.

Debug logging does not remove this requirement. Sensitive values must not be
logged even during local development.

See :doc:`../security/secrets` for the general secret-handling policy.


Testing
-------

The logging configuration is covered by ``tests/test_logging.py``.

The tests verify:

* supported and invalid log levels;
* log-level normalisation;
* development and production formatters;
* local rotating file logging;
* production console-only logging;
* independently configured logger levels;
* propagation behaviour.

See :doc:`testing` for the general testing and coverage policy.
