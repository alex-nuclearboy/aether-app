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

``.env.example`` is intentionally limited to the local development setup.
Production-only and provider-specific configuration is managed separately
through the deployment environment and documented in the configuration
reference and the relevant deployment or integration documentation.

The template sets ``AETHER_ENVIRONMENT=development``. Keep this value for the
normal local workflow.

The local security defaults deliberately leave HTTPS redirection, secure-only
cookies, and HSTS disabled because Django's development server is normally
accessed over HTTP. These development defaults are not the production security
policy.

See :doc:`../security/django` for the security configuration model.

Configure the Django secret key
-------------------------------

Generate a local Django secret key::

   uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

Copy the generated value into ``DJANGO_SECRET_KEY`` in ``.env``.

Local email
-----------

The local ``.env.example`` configures:

.. code-block:: text

   DJANGO_DEFAULT_FROM_EMAIL=aether@example.com

Development uses Django's console email backend. Queued verification and
password-reset messages are printed by their **separate worker processes**,
not by the Django development server, and are not sent to an external service.
The automated test suite may use Django's in-memory mail backend instead.

No SMTP credentials are required for local development. Production SMTP
configuration is intentionally not included in ``.env.example``.

See :doc:`../integrations/mailjet` for the currently selected production email
provider.

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

The development server listens at http://127.0.0.1:8000/.

The public home page is available at http://127.0.0.1:8000/. It currently
contains a minimal interface built with the shared Django base template.

The Django administration interface remains available at
http://127.0.0.1:8000/admin/.

Test email verification and password reset locally
--------------------------------------------------

Keep ``runserver`` open in the first terminal and PostgreSQL running. To
process verification messages in a second terminal::

   uv run python manage.py process_verification_email_queue --once --public-origin=http://127.0.0.1:8000

To process password-reset messages in a separate terminal::

   uv run python manage.py process_password_reset_queue --once --public-origin=http://127.0.0.1:8000

The ``--once`` option processes at most one queued message. Omit it to keep a
worker polling. Each command consumes **only its own** PostgreSQL queue.
Messages (including the confirmation link) appear in that worker's console;
no real email or SMTP credentials are needed locally. Avoid copying live
tokens into application logs or bug reports.

The public ``/password/reset/`` page is available even with
``AETHER_REGISTRATION_ENABLED=False``. Request a reset for an eligible test
account, run its worker, follow the printed link, and set a new password.
Django first redirects a valid token-bearing link to a session-backed
``set-password`` URL. After the password change, confirm that the previous
link no longer works and sign in explicitly with the new password. For a
public-registration account, the email must first be verified; existing
accounts without ``email_verification_required`` retain their established
sign-in and password-recovery policy.

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
