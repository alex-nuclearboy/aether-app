
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

The current implementation provides the authentication backend only.

Login and logout views, forms, URLs, and templates have not yet been
introduced.

Authentication audit logging will be implemented separately using
Django authentication signals.
