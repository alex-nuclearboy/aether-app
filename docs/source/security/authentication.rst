Authentication
==============

Aether uses a custom user model based on Django's ``AbstractUser`` and
a custom authentication backend based on ``ModelBackend``.

Account identifiers
-------------------

Users can authenticate using either their username or email address.

The authentication backend receives the identifier through Django's
standard ``username`` credential.

Identifiers containing ``@`` are resolved through ``email__iexact``.
Other identifiers are resolved through ``username__iexact``.

Both lookups are case-insensitive. The original casing of stored
identifiers is preserved.

The username validation rules prohibit ``@`` in usernames.
Database-level case-insensitive unique constraints prevent ambiguous
matches.

Password verification
---------------------

Password verification uses Django's standard password machinery.

Django's timing-attack mitigation is retained for unknown accounts.
Incorrect passwords and inactive users are rejected.

Both synchronous and asynchronous authentication are supported.

The backend does not explicitly log submitted credentials or passwords.
Sensitive password variables are protected in exception reports.

Brute-force protection
----------------------

Aether uses ``django-axes`` to protect authentication against repeated
failed login attempts.

``AsyncAxesStandaloneBackend`` extends django-axes'
``AxesStandaloneBackend`` and runs before the project's
``UsernameOrEmailBackend``.

It delegates asynchronous lockout checks to the original synchronous
Axes implementation through ``sync_to_async``, ensuring consistent
lockout enforcement for synchronous and asynchronous authentication.

Django's standard password verification, active-user checks, and
permission handling remain unchanged.

Lockout policy
~~~~~~~~~~~~~~

Authentication is blocked after three failed attempts for the same
account identifier and client IP address.

The lockout lasts 15 minutes. Correct credentials are also rejected
while the corresponding identifier and IP combination is locked.

Additional attempts during the lockout do not extend the cool-off period.
A successful login resets the corresponding failure counter.

Different accounts and client IP addresses maintain independent counters.

Identifier normalisation
~~~~~~~~~~~~~~~~~~~~~~~~

The ``accounts.lockouts.get_lockout_username`` function provides a
canonical account identifier for django-axes.

Known usernames and email addresses are resolved to the same
case-normalised username. Unknown identifiers are normalised without
creating or modifying user accounts.

This prevents switching between username and email to bypass the
failure threshold.

Client IP resolution
~~~~~~~~~~~~~~~~~~~~

The Axes client IP callable uses the shared
``infrastructure.request.get_client_ip`` function.

Authentication protection therefore follows the project's existing
client IP resolution policy.

The reverse-proxy trust assumptions are documented in :doc:`django`.

Persistence
~~~~~~~~~~~

Authentication attempts are tracked in PostgreSQL using the Axes
database handler.

The required database tables are created by the migrations provided
with django-axes. No additional accounts migrations are required.

The Axes database records are used for authentication attempt tracking and
lockout enforcement. Authentication audit events are handled separately
through the existing logging system and do not require additional database
tables.

Current lockout response
~~~~~~~~~~~~~~~~~~~~~~~~

The current implementation returns HTTP 429 when the failure limit is
reached. A custom ``AXES_LOCKOUT_CALLABLE`` returns the current remaining
time in the HTTP ``Retry-After`` header (seconds) for each blocked request,
with ``Cache-Control: no-store``. The response body contains a generic
message without revealing whether the submitted account exists.

No dedicated lockout status page or browser countdown has been implemented
yet. Visiting the normal Django Admin login page (GET) is not itself a failed
authentication attempt; the future lockout page will use the same timing
helpers to refresh its countdown.

``accounts.lockouts.get_lockout_deadline`` determines the absolute deadline
of an active username/IP lockout from django-axes database records.
``accounts.lockouts.get_lockout_remaining_seconds`` returns the current
non-negative remaining time. A future lockout view can recalculate this value
on every request, including page refreshes, without extending the lockout.

Authentication audit logging
----------------------------

Aether records successful login, failed login before lockout,
authenticated logout, newly triggered lockout, and subsequent blocked login
attempts. Django's ``user_logged_in``, ``user_logged_out``, and
``user_login_failed`` signals and django-axes' ``user_locked_out`` signal
are handled in ``accounts/audit.py``. Receivers are registered through
``AccountsConfig.ready()`` in ``accounts/apps.py``.

The current audit events are:

* ``authentication.login_success`` (``INFO``);
* ``authentication.logout`` (``INFO``);
* ``authentication.login_failed`` (``INFO``);
* ``authentication.lockout`` (``WARNING``);
* ``authentication.lockout_denied`` (``WARNING``).

Login and logout messages include the internal ``user_id`` and the client IP
resolved through ``infrastructure.request.get_client_ip``. Anonymous logout
signals are ignored.

Lockout messages include a keyed SHA-256 HMAC fingerprint of the normalised
login identifier, the resolved client IP address, failure count, configured
cool-off duration, remaining-time snapshot, and deadline. The deadline is
formatted in UTC with second-level precision. The remaining-time value is
calculated when the event is recorded; it is not updated in the audit log.
Custom failed-login and lockout messages do not expose plaintext usernames,
email addresses, or credentials.

Repeated blocked attempts do not extend the lockout or produce additional
``authentication.lockout`` events. Each blocked authentication POST instead
produces ``authentication.lockout_denied`` with a recalculated remaining-time
snapshot; GET requests do not create such events. django-axes
continues to manage failed-attempt records and enforcement in PostgreSQL,
with its standard sensitive-parameter masking unchanged.

The audit receivers also cover Django Admin and can be reused by future
application-specific views that use Django's authentication mechanisms.

See :doc:`../development/logging` for the log format, destinations, and
sensitive-data handling.


Authorization
-------------

Authentication and authorization are separate responsibilities.

The backend inherits Django's standard group and permission behaviour
from ``ModelBackend``.

Aether does not currently define application-specific roles or access
policies. Those rules will be introduced alongside the features they
protect.

The ``is_staff`` flag controls eligibility for Django administration,
not an application-specific access level.

Implementation scope
--------------------

The current implementation provides username-or-email authentication
and brute-force protection through django-axes.

Django Admin uses the protected authentication flow.

Application-specific login and logout views, forms, URLs, and templates
have not yet been introduced.

A dedicated lockout status page has not yet been implemented.
