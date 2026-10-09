Architecture overview
=====================

Aether is currently a Django web application with PostgreSQL as its required
database backend.

Current foundation
------------------

The implemented foundation consists of:

* Django 6.1;
* environment-driven settings through ``django-environ``;
* PostgreSQL access through Psycopg 3;
* PostgreSQL 18 for local development through Docker Compose;
* dependency and virtual-environment management through ``uv``;
* Pylint with Django-aware linting;
* Sphinx documentation;
* GitHub Actions for continuous quality checks.

The application layer is intentionally minimal at this stage. Product domains,
service boundaries, background work, and external-provider adapters should be
documented when they are introduced rather than being assumed in advance.

Confirmed platform direction
----------------------------

The planned production target is Koyeb for the Django application and Neon for
managed PostgreSQL. Production deployment has not yet been implemented.

Google Calendar, external APIs, and cloud-backed file storage are confirmed
integration areas. Their concrete architecture, permissions, synchronisation
behaviour, and provider-specific configuration will be documented alongside
the corresponding implementation.
