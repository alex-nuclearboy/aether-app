
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

``AxesStandaloneBackend`` runs before the project's
``UsernameOrEmailBackend``. Django's standard password verification,
active-user checks, and permission handling remain unchanged.

Lockout policy
~~~~~~~~~~~~~~

Authentication is blocked after three failed attempts for the same
account identifier and client IP address.

The lockout lasts 15 minutes. Correct credentials are also rejected
while the corresponding identifier and IP combination is locked.

Additional attempts during the lockout do not extend the cool-off period.
Successful authentication resets the corresponding failure counter.

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

Authentication audit logging remains a separate concern.

Current lockout response
~~~~~~~~~~~~~~~~~~~~~~~~

The current implementation returns HTTP 429 when the failure limit
is reached.

A dedicated lockout status page with a server-rendered remaining-time
indicator will be introduced separately.

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

A dedicated lockout status page and authentication audit logging will
be implemented separately.
