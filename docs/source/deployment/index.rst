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
Registration POST is available only under an explicit development/test
flag and enforces PostgreSQL-backed per-IP limits. The account and outbox job
are created atomically; authenticated profile requests also enqueue jobs.
Public resend is implemented with IP and address limits. Email correction,
verification of the Koyeb-only ingress trust boundary and scheduled
counter cleanup remain incomplete. Production client-IP resolution now
requires the final Koyeb-added ``X-Forwarded-For`` value and does not fall
back to ``REMOTE_ADDR``. Registration must remain disabled in production.

The independent verification email worker supports PostgreSQL leases,
retries, lease recovery and an explicit public origin. SMTP no longer runs
in registration or profile HTTP requests. The worker is **not** started by
the web process: delivery requires a separately deployed and monitored worker.
Before production use, configure a verified HTTPS public origin and test SMTP
failures, template and backend exceptions, worker restarts, lease recovery and
retention of failed jobs. The continuous command logs an exception type and
pauses for at least five seconds after unexpected infrastructure failures;
the ``--once`` mode fails visibly instead. Provision monitoring for repeated
worker errors and terminally failed jobs before enabling production delivery.

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
