Architecture overview
=====================

Aether is currently a Django web application with PostgreSQL as its required
database backend.

Current foundation
------------------

The implemented foundation consists of:

* Django 6.1;
* environment-driven settings through ``django-environ``;
* explicit ``development``, ``test``, and ``production`` runtime environment
  classification;
* production safety validation for debug mode, allowed hosts, and secure
  session and CSRF cookies;
* PostgreSQL access through Psycopg 3;
* PostgreSQL 18 for local development through Docker Compose;
* dependency and virtual-environment management through ``uv``;
* automated testing through ``pytest`` and ``pytest-django``;
* branch coverage reporting and enforcement through ``pytest-cov``;
* configurable application logging with coloured development output through
  ``colorlog``;
* environment-specific email delivery through Django ``MAILERS``, using the
  console backend in development and test environments and authenticated SMTP
  in production;
* compatibility validation across Python 3.12, 3.13, and 3.14;
* installed-dependency consistency checking through ``uv pip check``;
* dependency vulnerability auditing through ``uv audit``;
* repository-level dependency vulnerability monitoring and security update
  pull requests through GitHub Dependabot;
* Pylint with Django-aware linting;
* Sphinx documentation;
* GitHub Actions for continuous quality, compatibility, and security checks.

The application layer is intentionally minimal at this stage. Product domains,
service boundaries, background work, and external-provider adapters should be
documented when they are introduced rather than being assumed in advance.

Confirmed platform direction
----------------------------

The planned production target is Koyeb for the Django application and Neon for
managed PostgreSQL. Production deployment has not yet been implemented.

Mailjet is the currently selected provider for production transactional email
delivery. It is connected through the provider-neutral SMTP configuration
documented in :doc:`../integrations/mailjet`.

Google Calendar, external APIs, and cloud-backed file storage remain confirmed
future integration areas. Their concrete architecture, permissions, synchronisation
behaviour, and provider-specific configuration will be documented alongside
the corresponding implementation.
