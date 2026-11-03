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
cookies. The current configuration also rejects
``AETHER_REGISTRATION_ENABLED=True`` in production, pending public email
recovery and anti-abuse controls. The setting defaults to ``False``.
The registration POST and verification-email trigger can currently be
exercised only under an explicit development/test flag. The staged endpoint
now enforces PostgreSQL-backed per-IP limits, but public email recovery,
durable delivery, trusted production client-IP configuration and scheduled
counter expiry cleanup are not yet complete. Registration must not be enabled
in production.

The independent verification email worker now supports PostgreSQL leases,
retry and lease recovery, and an explicit public origin. It is not started by
the web process, and existing HTTP views still use synchronous SMTP. Before
queued delivery can be enabled in production, deploy and monitor a separate
worker process, configure a verified HTTPS public origin, and test SMTP
failures, worker restarts and retention of failed jobs.

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
