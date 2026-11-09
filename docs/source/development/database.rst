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

Account identifier constraints
------------------------------

The ``accounts.User`` model uses database constraints to protect account
identifiers. In PostgreSQL, ``Lower("username")`` and ``Lower("email")``
unique constraints prevent duplicates differing only in letter case.

The ``accounts_user_email_not_blank`` check constraint requires at least one
non-whitespace character in each email value. It applies even when user
records are inserted or updated through ORM operations that bypass
``AetherUserManager``. This is a presence constraint, not complete email
syntax validation. Django forms and the custom user manager validate syntax
on their respective creation paths.

Before applying an email-constraint migration to a database containing user
records, check for existing empty or whitespace-only addresses and resolve
any violations. Keep historical migrations intact; generate new migrations
when user-model constraints change.

See :doc:`../security/authentication` for account-creation rules and
:doc:`testing` for PostgreSQL constraint tests.

Public request counters
-----------------------

``accounts.PublicRequestCounter`` holds pseudonymous request counters in
PostgreSQL. Fixed-window keys are derived using a separate keyed HMAC context;
identifiers are not stored in plaintext. The records have an indexed expiry
time for later removal by a worker or maintenance command.

Staged registration POST uses this service to limit requests per client IP
address, including invalid form submissions. Public resend also enforces
separate IP and email allowances, without storing either identifier in
plaintext. Email correction is not yet connected. Fixed UTC windows can
permit boundary bursts; further protection is required before production.

A management command removes expired counters in configurable batches::

   uv run python manage.py prune_public_request_counters --dry-run
   uv run python manage.py prune_public_request_counters --batch-size 1000

The command deletes only records whose expiry has passed; it leaves current
allowances intact. It must be scheduled as part of the future production
maintenance configuration. It does not run automatically during HTTP requests.

Verification email outbox and worker
------------------------------------

``accounts.VerificationEmailJob`` stores a snapshot of the intended recipient
and scheduling information for the independent delivery worker. Active jobs have a
conditional PostgreSQL uniqueness constraint on user and recipient. Jobs do
not contain verification tokens or rendered messages.

``accounts.email_outbox.queue_verification_email()`` reserves a job and the
existing account-level request timestamp in one atomic transaction. Repeated
requests for an active job are idempotent, and a verified address is not
queued. An address change can produce a separate job; the worker checks the
recipient snapshot against the current address before delivery.

The worker in ``accounts.email_worker`` now claims due rows using
PostgreSQL ``SELECT FOR UPDATE SKIP LOCKED``. A lease expires after five
minutes; abandoned work can then be reclaimed. SMTP I/O occurs outside the
transaction. Success, cancellation and failure updates match the original
lease to prevent a previous worker from overwriting a newer claim.

Transport failures and unexpected errors during token generation, template
rendering or mail-backend delivery use the same bounded backoff (at most
five attempts). The database records only ``transport``, ``preparation`` or
``delivery`` error categories, never exception messages or verification
URLs. Unexpected failures are logged with the job ID and exception type only.
After the final unsuccessful attempt, the job becomes ``failed``. Expired
leases at the retry limit also become terminal failures.
Before sending, the worker cancels jobs for inactive accounts, changed
recipient addresses or already verified addresses. A job cancelled because
its account is inactive records ``inactive_user`` as its error category.
The check is not atomic with SMTP delivery: deactivation after the check
may still race with an in-progress send. Verification tokens are created
at delivery time and are never persisted in the queue.

The worker is operated separately using ``process_verification_email_queue``
and a required trusted public origin. It is **not automatically started** by
the Django HTTP server. Registration and authenticated profile views already
enqueue jobs without SMTP I/O; delivery requires a running worker. SMTP
delivery is at least once, not exactly once: a crash after SMTP acceptance
can result in a duplicate message on lease recovery. An unexpected database
or claim-finalisation error leaves the current lease in place; the continuous
management command logs the exception type, waits at least five seconds,
and resumes polling. A leased job can be reclaimed after lease expiry. The
``--once`` command instead exits with an error for such infrastructure faults.

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
