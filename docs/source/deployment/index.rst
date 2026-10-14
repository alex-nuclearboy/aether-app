Deployment
==========

Production deployment has not yet been implemented.

The confirmed target is:

* Koyeb for hosting the Django application;
* Neon for managed PostgreSQL.

The current settings are designed so production can provide ``DATABASE_URL``
and other configuration through environment variables without maintaining a
separate production settings module.

Production must explicitly declare ``AETHER_ENVIRONMENT=production``. The
current settings then require Django debug mode to be disabled, require a
non-wildcard allowed-host configuration, and require secure session and CSRF
cookies.

The production runtime also requires email delivery configuration: a default
sender address together with a configured SMTP host and authentication
credentials. Aether keeps this application-level SMTP configuration
provider-neutral.

Mailjet is the currently selected production email provider. Its SMTP endpoint,
credential mapping, sender verification requirements, and operational setup are
documented in :doc:`../integrations/mailjet`.

The exact mapping of email configuration to Koyeb environment variables and
Secrets will be documented when the production deployment is implemented and
verified.

HTTPS redirect ownership, trusted proxy headers, and the final HSTS policy have
not yet been fixed because they depend on the verified Koyeb deployment
architecture.

See :doc:`../security/django` for the implemented security baseline.

The local Docker Compose PostgreSQL service is development infrastructure only
and is not intended to provide the production database.

This section will be expanded when deployment work begins. The documentation
should then record the tested Koyeb build and start configuration, Neon
connection mode, database migrations, static-file handling, health checks,
security settings, logging, and operational procedures actually used by the
project.
