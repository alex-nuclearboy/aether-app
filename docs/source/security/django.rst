Django security configuration
=============================

Aether applies security-sensitive Django configuration through environment
variables and validates a small set of provider-independent production
requirements during settings loading.

Runtime environment
-------------------

The runtime environment is declared explicitly through
``AETHER_ENVIRONMENT``.

The supported environments are:

* ``development``;
* ``test``;
* ``production``.

Environment identity is intentionally separate from ``DJANGO_DEBUG``.
``DEBUG=False`` does not imply production, and production is not inferred from
the value of the Django debug setting.

This distinction allows development, automated tests, CI, and future deployment
environments to use appropriate Django settings without accidentally activating
or bypassing production validation.

Production safeguards
---------------------

When ``AETHER_ENVIRONMENT=production``, the Django security baseline requires:

* ``DJANGO_DEBUG=False``;
* at least one value in ``DJANGO_ALLOWED_HOSTS``;
* no ``*`` wildcard in ``DJANGO_ALLOWED_HOSTS``;
* ``DJANGO_SESSION_COOKIE_SECURE=True``;
* ``DJANGO_CSRF_COOKIE_SECURE=True``.

Production settings also validate operational configuration that is not part of
this security baseline, including the default email sender and SMTP connection
settings. See :doc:`../architecture/configuration` and
:doc:`../integrations/mailjet`.

Invalid production configuration fails immediately with
``ImproperlyConfigured`` rather than allowing the application to start with a
known unsafe configuration.

CSRF trusted origins
--------------------

Additional trusted origins can be supplied through
``DJANGO_CSRF_TRUSTED_ORIGINS``.

Configured origins are normalised by removing surrounding whitespace and a
trailing slash. An empty list is valid, including for deployments that do not
require additional cross-origin CSRF trust.

HTTPS redirection
-----------------

``DJANGO_SECURE_SSL_REDIRECT`` controls Django's
``SECURE_SSL_REDIRECT`` setting and defaults to ``False``.

It is intentionally not enforced as a generic production invariant yet.
Whether Django or the deployment platform should perform HTTP-to-HTTPS
redirection depends on the verified production proxy architecture.

The project therefore does not currently configure
``SECURE_PROXY_SSL_HEADER``. Trusting a forwarded protocol header will be
considered only after the production proxy behaviour has been verified.

Client IP resolution
--------------------

Aether uses a shared client IP resolver in ``infrastructure.request``.

Development and test environments use ``REMOTE_ADDR`` and do not trust
client-supplied forwarding headers.

Production is currently configured for the documented Koyeb ingress
behaviour. Koyeb appends the connecting peer address to the end of
``X-Forwarded-For``. The resolver selects the final address rather than
trusting earlier entries, which may have been supplied by the client.

The resolved address is validated and normalised using Python's
``ipaddress`` module. Invalid addresses return ``None``.

The production policy assumes that requests reach the application through
the trusted Koyeb ingress. The ingress restriction and actual forwarded
headers must be verified before deployment.

If another proxy or CDN is introduced, the address resolution policy must
be reviewed. The selected address may otherwise identify an upstream proxy
rather than the originating client.

The shared resolver is used by django-axes for authentication lockout
protection and can be reused by future components, including audit logging.

Client IP resolution is separate from Django's HTTPS proxy settings.
``SECURE_PROXY_SSL_HEADER`` remains unconfigured at this stage.

Secure cookies
--------------

Session and CSRF cookies are allowed to remain non-secure during normal local
HTTP development.

Production is different: both ``SESSION_COOKIE_SECURE`` and
``CSRF_COOKIE_SECURE`` are mandatory. This requirement is independent of which
component ultimately performs HTTP-to-HTTPS redirection.

HTTP Strict Transport Security
------------------------------

HSTS is configured through:

* ``DJANGO_SECURE_HSTS_SECONDS``;
* ``DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS``;
* ``DJANGO_SECURE_HSTS_PRELOAD``.

The HSTS duration defaults to ``0`` and must not be negative.

Aether does not yet require a positive HSTS duration in production. HSTS
duration, subdomain coverage, and preload policy will be selected only after
the real HTTPS deployment has been verified.

Development and test environments
---------------------------------

The local template uses ``AETHER_ENVIRONMENT=development`` and keeps HTTPS
redirection, secure cookies, and HSTS disabled so that Django's local
development server can operate over HTTP.

Automated project settings tests use ``AETHER_ENVIRONMENT=test``. This keeps
test execution explicitly separate from production even when an individual
test or CI environment uses ``DJANGO_DEBUG=False``.

Testing
-------

``tests/test_settings.py`` verifies the security configuration model,
including:

* runtime environment normalisation and validation;
* valid production configuration;
* rejection of debug mode in production;
* production allowed-host requirements;
* production secure-cookie requirements;
* trusted-origin normalisation;
* environment-controlled security overrides;
* rejection of negative HSTS duration.

GitHub Actions also runs ``manage.py check --deploy --fail-level WARNING`` in a
separate ``deployment-checks`` job using synthetic production-shaped values.
This verifies the production settings path without treating those CI values as
the final deployment configuration.

Deployment-specific HTTPS, proxy-header, and HSTS decisions remain outside this
baseline until the production platform is implemented and verified.

See :doc:`../reference/environment-variables` for the complete variable
reference and :doc:`../architecture/configuration` for the wider configuration
model.
