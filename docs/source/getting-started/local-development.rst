Local development
=================

Requirements
------------

The recommended local environment requires:

* Python 3.14;
* ``uv``;
* Docker with Docker Compose support;
* Git.

Aether currently supports Python 3.12 through 3.14.

Install the project
-------------------

Clone the repository and synchronise the project environment::

   git clone https://github.com/alex-nuclearboy/aether-app.git
   cd aether-app
   uv sync

Create the local environment file
---------------------------------

Copy ``.env.example`` to ``.env`` using the command appropriate for the local
platform.

Windows Command Prompt::

   copy .env.example .env

Windows PowerShell::

   Copy-Item .env.example .env

Linux and macOS::

   cp .env.example .env

The local ``.env`` file contains development configuration and credentials. It
is ignored by Git and must not be committed.

Configure the Django secret key
-------------------------------

Generate a local Django secret key::

   uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

Copy the generated value into ``DJANGO_SECRET_KEY`` in ``.env``.

Configure the PostgreSQL password
---------------------------------

Set a development-only value for ``POSTGRES_PASSWORD``. You can choose one
manually or generate a random URL-safe value::

   uv run python -c "import secrets; print(secrets.token_urlsafe(32))"

When choosing the value manually, use only ASCII letters, digits, hyphens
(``-``), and underscores (``_``). Avoid URL-reserved characters such as ``@``,
``:``, ``/``, ``?``, ``#``, ``%``, ``&``, ``+``, and ``=`` because the same raw
value is inserted directly into ``DATABASE_URL``.

The remaining local PostgreSQL values can normally keep the defaults from
``.env.example``. See :doc:`../reference/environment-variables` for the full
configuration reference.

Start PostgreSQL
----------------

Start the local PostgreSQL service::

   docker compose up -d

Check its status::

   docker compose ps

Wait until the database reports a ``healthy`` status before running commands
that require a database connection.

Initialise Django
-----------------

Apply the committed migrations::

   uv run python manage.py migrate

Create a local superuser for Django administration::

   uv run python manage.py createsuperuser

Django prompts for a username, email address, and password. The local
superuser is for development and administration only; do not reuse production
credentials.

Run the application
-------------------

Start the Django development server::

   uv run python manage.py runserver

The application is available at http://127.0.0.1:8000/ and the Django
administration site at http://127.0.0.1:8000/admin/.

Stop the local environment
--------------------------

Stop the Django development server with ``Ctrl+C`` in the terminal where
``runserver`` is running.

Then stop and remove the PostgreSQL container and Compose network::

   docker compose down

The named PostgreSQL volume is preserved, so the local database remains
available the next time the service is started.

To remove the local database data as well, the volume must be deleted
explicitly. Do not use ``docker compose down -v`` unless a complete local
database reset is intended.
