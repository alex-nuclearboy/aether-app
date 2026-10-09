Deployment
==========

Production deployment has not yet been implemented.

The confirmed target is:

* Koyeb for hosting the Django application;
* Neon for managed PostgreSQL.

The current settings are designed so production can provide ``DATABASE_URL``
and other configuration through environment variables without maintaining a
separate production settings module.

The local Docker Compose PostgreSQL service is development infrastructure only
and is not intended to provide the production database.

This section will be expanded when deployment work begins. The documentation
should then record the tested Koyeb build and start configuration, Neon
connection mode, database migrations, static-file handling, health checks,
security settings, logging, and operational procedures actually used by the
project.
