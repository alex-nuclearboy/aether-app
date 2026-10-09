Local database
==============

Aether uses PostgreSQL as its database backend. Local development runs
PostgreSQL 18 in Docker Compose, while Django itself runs on the host machine.

Local topology
--------------

The local connection path is::

   Django
      |
      v
   127.0.0.1:${POSTGRES_PORT}
      |
      v
   Docker Compose
      |
      v
   PostgreSQL 18

The database port is published only on ``127.0.0.1``. It is therefore intended
for access from the local machine rather than from other hosts on the network.

Persistent data
---------------

PostgreSQL data is stored in the named ``postgres_data`` Docker volume. Normal
container shutdown or recreation does not remove this volume.

The following command stops and removes the Compose container and network while
preserving the database data::

   docker compose down

Using ``docker compose down -v`` also removes the named volume and therefore
deletes the local PostgreSQL data. Use it only when a complete reset is
intended.

Configuration flow
------------------

Docker Compose reads the local PostgreSQL values from ``.env``:

* ``POSTGRES_DB``;
* ``POSTGRES_USER``;
* ``POSTGRES_PASSWORD``;
* ``POSTGRES_PORT``.

Django uses ``DATABASE_URL``. In the local environment the URL contains
``${...}`` references to the PostgreSQL values. The project settings expand
those references before ``django-environ`` parses the URL.

The database settings then validate that the result is a PostgreSQL connection
and configure connection lifetime, health checks, and the connection timeout.
See :doc:`../architecture/configuration` for the configuration model and
:doc:`../reference/environment-variables` for individual variables.

Useful commands
---------------

Inspect the service status::

   docker compose ps

Read PostgreSQL logs::

   docker compose logs db

Open ``psql`` inside the running container::

   docker compose exec db psql -U aether -d aether

Apply Django migrations::

   uv run python manage.py migrate
