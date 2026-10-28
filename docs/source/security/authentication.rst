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

User creation and email validation
----------------------------------

Every Aether user account requires an email address. The ``User`` model uses
``AetherUserManager`` from ``accounts/managers.py`` as its default manager.
The manager rejects missing, blank, malformed, and excessively long email
addresses during ``create_user()``, ``create_superuser()``,
``acreate_user()``, and ``acreate_superuser()``. It uses Django's standard
``EmailField`` validation and preserves the usual email-domain normalisation.

Django administration uses its standard user forms. The configured add form
includes a required email field, which is validated before saving. The
``createsuperuser`` management command also requires an email address.

PostgreSQL enforces email uniqueness without regard to letter case and rejects
empty or whitespace-only email values. These database constraints apply to
direct ORM writes, including operations that bypass the user manager. They do
not validate complete email syntax: ``save()``, ``objects.create()``, and
``QuerySet.update()`` do not automatically run model field validation.

Model field labels, project-defined validation messages, and the additional
Django Admin fieldset label use Django's translation mechanisms to support
future interface localisation.

These checks validate address format and presence, **not ownership**. Email
verification links, public registration, and activation links have not yet
been implemented. Creating a user through Django Admin or ``createsuperuser``
does not send an email verification message.

Email verification state
------------------------

The ``User`` model stores the last explicitly verified address in
``verified_email``. New accounts have an empty value and are therefore
unverified. The read-only ``is_email_verified`` property returns ``True``
only when ``verified_email`` is non-empty and matches the user's current
``email`` case-insensitively. Changing ``email`` to a different address makes
this property ``False`` without requiring custom ``save()`` logic.

The verification state is independent of Django's ``is_active`` flag. Marking
an email as verified does not grant login access or reactivate an inactive
account. The ``verified_email`` field is excluded from ordinary model forms.

No email is verified automatically by account creation. Token generation,
confirmation links, sending messages, and profile controls have not yet been
implemented. The state will be updated only after a future verification
workflow confirms control of the address.

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
with django-axes. No additional accounts migrations are required for Axes
lockout tracking; separate accounts migrations manage user-model constraints.

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
yet. Visiting either login page (GET) is not itself a failed authentication
attempt; a future lockout page can use the same timing helpers to refresh
its countdown.

``accounts.lockouts.get_lockout_deadline`` determines the absolute deadline
of an active username/IP lockout from django-axes database records.
``accounts.lockouts.get_lockout_remaining_seconds`` returns the current
non-negative remaining time. A future lockout view can recalculate this value
on every request, including page refreshes, without extending the lockout.

Application login and logout
----------------------------

Aether provides its own sign-in page at ``/login/`` and a sign-out endpoint
at ``/logout/``. Both use Django's session authentication infrastructure.
The Django Admin login remains available separately at ``/admin/login/``.

``AetherLoginView`` extends Django's ``LoginView`` and uses
``AetherAuthenticationForm``. The form accepts either a username or an email
address via Django's standard ``username`` credential and displays one
neutral error message for invalid credentials. It does not implement
password verification or authentication separately from the existing backend.

Login POST requests are CSRF-protected. On success, users return to the
``home`` route by default. Django's standard safe-redirect handling
permits an internal ``next`` target while rejecting external destinations.

``AetherLoginView`` creates a one-time Django success message after
successful authentication. Invalid credentials produce neutral
validation feedback within the login form.

The shared fixed header offers a sign-in link to anonymous visitors and
a CSRF-protected sign-out form to authenticated users.
``AetherLogoutView`` extends Django's ``LogoutView``, accepts POST
requests only, invalidates the session, redirects to ``home``, and
creates a one-time success message. The public home page remains
accessible without authentication.

Django Admin and the application login share the Axes failure counters,
15-minute lockouts, HTTP 429 responses, request IDs, and audit signals.
Authentication forms do not duplicate those mechanisms. Dedicated
account registration, password reset, and lockout-status pages are not
implemented.


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

All authentication audit events include ``identifier_hash`` and
``client_ip``. Successful login and authenticated logout events also
include ``user_id``, identifying the verified authenticated user.

Failed login and lockout events do not contain ``user_id``, even when
the submitted identifier corresponds to an existing account. A claimed
account identity must not be confused with an authenticated user.

The identifier fingerprint is calculated from the canonical username
using a keyed SHA-256 HMAC. Known usernames and email addresses belonging
to the same account produce the same fingerprint.

New lockout events additionally include the failure count, configured
cool-off duration, remaining-time snapshot, and UTC deadline. The
deadline is formatted with second-level precision. Repeated blocked
attempts include an updated remaining-time snapshot.

Request IDs are assigned independently of account identifiers and included
in request-scoped server logs through the shared logging filter. They connect
messages from the same HTTP request but are not evidence of authenticated
identity. See :doc:`../development/logging` for request correlation.

Custom authentication audit events do not expose plaintext usernames,
email addresses, passwords, or submitted credentials.

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

The current implementation provides validated email requirements for account
creation, username-or-email authentication, application login and logout, and
brute-force protection through django-axes. Django Admin and the application
use the same protected authentication flow. Public registration, email
ownership verification, password reset, and dedicated lockout-status pages
remain outside the current scope.
