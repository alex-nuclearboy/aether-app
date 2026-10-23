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

Production logs are therefore emitted through the console handler, where they
can be collected by the hosting platform.


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
   Records security-relevant audit events independently of general application
   logging. It defaults to ``INFO`` in all environments.


Request correlation
-------------------

Aether assigns a new server-generated request ID to every HTTP request via
``infrastructure.request_id.request_id_middleware``. Each ID is a random UUID
represented as 32 hexadecimal characters. The ID is exposed through
``request.request_id`` and the ``X-Request-ID`` response header. Incoming
client-supplied request IDs are not trusted or reused.

The request middleware stores the ID in a ``ContextVar`` during request
processing and restores the previous context on completion, including when
processing raises an exception. Synchronous and asynchronous requests are
supported. Records outside request processing use ``request_id=-``.

``infrastructure.request_id.RequestIdFilter`` populates the ``request_id``
logging field for every configured console and file handler. This permits
messages from django-axes, Aether, and Django loggers produced during the
same request to be correlated without changing each log call.

The development server may emit its ``django.server`` access entry after the
middleware context has been cleared, so such access records can contain
``request_id=-``. Aether records an additional ``aether.http`` warning for
HTTP 429 responses within the active request context, including method,
path and status code. This is not a complete access log for all HTTP status
codes.

A request ID is neither an account identity nor a session identifier. Each
HTTP request receives a different ID; distributed tracing, a persistent
audit-event ID and cross-request correlation are not implemented yet.


Authentication audit events
---------------------------

``accounts/audit.py`` registers receivers for Django's authentication signals
and the django-axes lockout signal through ``AccountsConfig.ready()``.
Authentication security events are written to ``aether.audit``:

``authentication.login_success``
   Emitted at ``INFO`` level on successful authentication. Includes the
   verified ``user_id``, ``identifier_hash``, and ``client_ip``.

``authentication.logout``
   Emitted at ``INFO`` level on authenticated logout. Includes the
   verified ``user_id``, ``identifier_hash``, and ``client_ip``.
   Anonymous logout signals do not produce audit messages.

``authentication.login_failed``
   Emitted at ``INFO`` level for a rejected login before lockout. Includes
   ``identifier_hash`` and ``client_ip``. The threshold-crossing attempt is
   represented by ``authentication.lockout`` instead.

``authentication.lockout``
   Emitted at ``WARNING`` level when the failure threshold first triggers a
   lockout. Includes ``identifier_hash``, ``client_ip``, ``failures``,
   ``duration_seconds``, ``retry_after_seconds``, and ``locked_until``.

``authentication.lockout_denied``
   Emitted at ``WARNING`` level for a subsequent blocked authentication POST.
   Includes ``identifier_hash``, ``client_ip`` and the current
   ``retry_after_seconds``. Ordinary login-page GET requests are not logged
   as failed or denied authentication attempts.


Audit identity policy
~~~~~~~~~~~~~~~~~~~~~

Authentication audit events use ``identifier_hash`` and ``client_ip`` as
common fields. The internal ``user_id`` is included only when a user's
identity has been confirmed through successful authentication.

Failed login and lockout events do not include ``user_id``. This does not
indicate whether the submitted account identifier exists; it means that
the identity of the requester has not been authenticated.

The ``identifier_hash`` is calculated from the canonical username using
a keyed SHA-256 HMAC. Known username and email login identifiers resolve
to the same canonical username, allowing successful and unsuccessful
authentication events to be correlated without exposing plaintext
account identifiers.

The fingerprint is not a permanent account identifier. Changing a username
or rotating the secret key used by the HMAC may prevent correlation with
older audit records.

Client IP addresses are resolved using
``infrastructure.request.get_client_ip``. Passwords, submitted credentials,
and session identifiers are not included in custom authentication audit
messages.

``duration_seconds`` represents the configured cool-off duration.
``retry_after_seconds`` is the remaining time at the moment of the audit
event; it is a snapshot, not a live countdown. ``locked_until`` is the
absolute deadline, written in UTC with second-level precision and an
explicit UTC offset.

Deadlines are derived from django-axes database records through
``accounts.lockouts.get_lockout_deadline``. Subsequent requests can calculate
the current remaining time using
``accounts.lockouts.get_lockout_remaining_seconds``; neither helper reads
log messages. Repeated requests during an existing lockout do not extend its
deadline or repeat ``authentication.lockout``; blocked POST requests produce
separate ``authentication.lockout_denied`` audit events. Failed-attempt tracking
and lockout enforcement remain the responsibility of django-axes; its own
sensitive-data masking is unchanged.

``accounts.lockout_responses.lockout_response`` supplies HTTP 429 responses
with a dynamic ``Retry-After`` header in seconds and ``Cache-Control:
no-store``. The remaining time is recalculated for each blocked request,
independently of the audit log. No dedicated lockout page or browser
countdown is implemented yet.

Python's standard logging formatters provide the server log timestamp in the
running process's local time. Aether does not convert that timestamp using
Django's ``TIME_ZONE`` setting. A consistent server time-zone policy,
preferably UTC in production, simplifies cross-system correlation. This is
separate from the UTC ``locked_until`` field and from future user-facing
local-time presentation.

Client IP addresses and security-event metadata can be personal or sensitive
data. Audit log access and retention must be controlled appropriately.

Existing handlers route audit events to the development console and rotating
local log file, or to the production console.


Application logger naming
-------------------------

Application code that should use ``APP_LOG_LEVEL`` must log under the
``aether`` namespace.

For example::

   import logging

   logger = logging.getLogger("aether.example")

Child loggers such as ``aether.accounts`` or ``aether.integrations.google``
inherit the ``aether`` logger configuration.

This namespace is intentional. Loggers outside ``aether.*`` do not inherit the
application logging level unless they are configured separately.


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

Authentication audit events are tested in ``accounts/tests/test_audit.py``.
The tests cover successful and failed Django Admin logins, authenticated
and anonymous logout, fingerprint consistency across email and username,
lockout events, UTC deadlines, remaining-time snapshots, and suppression of
duplicate lockout threshold events.

Lockout timing and expiry are tested in ``accounts/tests/test_lockouts.py``.

See :doc:`testing` for the general testing and coverage policy.
