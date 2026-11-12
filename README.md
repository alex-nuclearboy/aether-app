# Aether

[![Code Quality](https://github.com/alex-nuclearboy/aether-app/actions/workflows/code-quality.yml/badge.svg)](https://github.com/alex-nuclearboy/aether-app/actions/workflows/code-quality.yml)

Aether is an early-stage personal digital environment built with Django. It is intended to provide a common layer for organising information, tasks, knowledge, files, integrations, and automation without coupling the core application to a single external service.

The current foundation includes environment-driven Django configuration, PostgreSQL, a custom user model, protected username-or-email sign-in, staged registration and email verification, pre-verification email correction, and a public password-reset flow. Verification and password-reset messages use separate PostgreSQL outboxes, independently operated workers, and shared leasing and retry infrastructure; both use console delivery in development. The project also provides authentication auditing, request IDs and sensitive-URL redaction, responsive shared templates, Docker Compose, `uv`, automated tests with branch coverage, Pylint, Sphinx documentation, GitHub Actions and Dependabot security monitoring.

## Requirements

For local development, you need:

- Python 3.14 (recommended)
- `uv`
- Docker with Docker Compose support
- Git

Aether currently supports Python 3.12–3.14.

Most development commands are platform-independent because Python tooling is run through `uv` and the local PostgreSQL database is provided through Docker Compose.

## Quick start

Clone the repository and install the project dependencies:

```console
git clone https://github.com/alex-nuclearboy/aether-app.git
cd aether-app
uv sync
```

### Create the local environment file

Copy `.env.example` to `.env`.

Windows Command Prompt:

```cmd
copy .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux and macOS:

```bash
cp .env.example .env
```

The `.env` file contains local configuration and credentials. It is ignored by Git and must not be committed to the repository.

The template sets `AETHER_ENVIRONMENT=development` for local use. Runtime environment classification is explicit and is independent of `DJANGO_DEBUG`. Keep the development value for the normal local workflow.

### Configure the Django secret key

Generate a local Django secret key:

```console
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value into `DJANGO_SECRET_KEY` in `.env`:

```dotenv
DJANGO_SECRET_KEY=
```

### Configure the PostgreSQL password

Set a local PostgreSQL password in `POSTGRES_PASSWORD`:

```dotenv
POSTGRES_PASSWORD=
```

You can either choose a development-only password yourself or generate a random URL-safe value:

```console
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the generated value into `POSTGRES_PASSWORD` in `.env`.

If you choose the password manually, use only ASCII letters, digits, hyphens (`-`), and underscores (`_`). Avoid URL-reserved characters such as `@`, `:`, `/`, `?`, `#`, `%`, `&`, `+`, and `=`, because the same value is inserted directly into `DATABASE_URL`.

The remaining local PostgreSQL settings can normally keep the defaults provided by `.env.example`.

### Start PostgreSQL

Start the local PostgreSQL service:

```console
docker compose up -d
```

Check its status:

```console
docker compose ps
```

Once initialisation is complete, the database should report a `healthy` status.

### Initialise the database

Apply the Django migrations:

```console
uv run python manage.py migrate
```

Create a Django superuser for access to the administration site:

```console
uv run python manage.py createsuperuser
```

Django will prompt you for a username, email address, and password. Email is required and validated; creating a superuser does not send an email verification message. The superuser account is intended for local administration and development; do not reuse production credentials.

### Run the application

Start the Django development server:

```console
uv run python manage.py runserver
```

The public home page is available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). It displays the full Aether logo in the centre of the main content area, beneath a fixed header containing a compact logo and a link to the home page.

The interface does not yet include a sidebar or additional navigation menus.

The Django administration site remains available at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

The public application sign-in page is available at
[http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/). Enter a username or email address and the account password. Anonymous users see **Sign in** and **Sign up** in the shared header; authenticated users see **My profile** and a POST-only **Sign out** control. The sign-in page also links to **Forgot your password?**. Registration remains disabled by default, independently of password recovery. Application login and Django Admin share brute-force protection and authentication auditing.

During local development, application logs are colourised in the console and are also written to the rotating `logs/aether.log` file. Logging levels can be controlled through the local environment configuration. See the [logging documentation](docs/source/development/logging.rst) for details.

### Correct a registration email before verification

The public `/register/correct-email/` page lets someone who entered the wrong
email during registration supply their username, registration password and
correct address. Only never-verified public registration accounts are eligible.
The request is rate-limited per client IP and username, returns a neutral result
and does not sign anyone in. If eligible, it cancels outstanding old-address
jobs and queues a replacement verification link atomically. The page is
available independently of the new-registration flag; production registration
is still disabled pending additional safeguards.

### Reset a forgotten password

The public [password-reset request page](http://127.0.0.1:8000/password/reset/)
accepts an email address independently of the registration gate. Valid requests
show a neutral result whether or not an eligible account exists. Eligible active
accounts must have a usable password and, when email verification is required,
a verified current address. PostgreSQL enforces independent per-IP and per-email
limits (10 and 3 POSTs per fixed UTC hour respectively), plus deduplication and
a one-minute account cooldown. The HTTP request creates an outbox job; it does
**not** send a message or sign the visitor in.

Run the separate password-reset worker in another terminal:

```console
uv run python manage.py process_password_reset_queue --public-origin=http://127.0.0.1:8000
```

Or process at most one job using `--once`. In development, this worker prints
the plain-text and HTML email to its own console, without external SMTP. Open
the link, follow Django's token-free intermediate URL, and set a new password.
A successful reset invalidates the old token but does **not** sign the user in.
The login page remains the entry point afterwards. An outstanding reset job is
removed when its user is deleted (by database cascade), or cancelled by the
worker if the account becomes ineligible or its password, email or login state
changes before delivery.

Password-reset jobs use their **own** PostgreSQL queue and worker. Starting
`process_verification_email_queue` does not process password resets.

### Process queued verification emails

Registration, profile verification, public resend and pre-verification email
correction requests queue email jobs in PostgreSQL;
they do not contact SMTP from HTTP requests. To process those jobs locally,
run the independent worker in a second terminal:

```console
uv run python manage.py process_verification_email_queue --public-origin=http://127.0.0.1:8000
```

The development mailer writes messages to this worker console. Stop the worker
with `Ctrl+C`, or pass `--once` to process at most one job. Failed delivery
uses bounded retries, including unexpected rendering and mail-backend errors.
The continuous worker also resumes polling after unexpected infrastructure
errors. Production requires an independently deployed and monitored worker,
with a trusted HTTPS public origin and SMTP configuration. See the
[deployment guide](docs/source/deployment/index.rst) for prerequisites.

To stop the development server, press `Ctrl+C` in the terminal where `runserver` is running. Then stop PostgreSQL with:

```console
docker compose down
```

The named database volume is preserved.

## Development checks

Run the current project checks before committing changes:

```console
uv lock --check
uv pip check
uv audit --preview-features audit-command --locked
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run python manage.py collectstatic --noinput --dry-run
uv run pytest
uv run pylint config accounts core infrastructure tests manage.py docs/source/conf.py
uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
```

GitHub Actions runs the full project checks against the preferred Python version defined in `.python-version`, verifies compatibility with Python 3.12 and 3.13, runs Django deployment checks against a synthetic production-shaped configuration, and audits the locked dependency graph for Python 3.12–3.14 on Linux.

The compatibility jobs use a temporary PostgreSQL 18 instance and run the Django checks, committed migrations, and automated test suite against the additional supported Python versions.

GitHub Dependabot provides an additional dependency-security layer. Dependabot alerts monitor supported dependencies for known vulnerabilities, and Dependabot security updates can open remediation pull requests when a compatible security fix is available.

Routine Dependabot version updates are intentionally disabled. Dependency upgrades that are unrelated to a known security issue remain a manual maintenance decision.

## Documentation

Detailed project documentation lives in [`docs/`](docs/README.md) and is built with Sphinx. It covers development workflows, PostgreSQL, automated testing and coverage, logging, architecture, configuration, CI, security, environment variables, commands, deployment status, and current and planned integrations.

Build the documentation from the repository root with:

```console
uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
```

The generated HTML is written to `docs/_build/html/` and is not committed to the repository.

## Deployment direction

The planned production environment uses Koyeb for application hosting and Neon for managed PostgreSQL. Mailjet is the currently selected provider for production email delivery. Aether is configured to use Mailjet through Django's standard SMTP backend.

Google Calendar, external APIs, and cloud-backed file storage remain planned integration areas. Detailed provider-specific configuration is maintained in the Sphinx documentation as integrations are implemented and verified.

## License

Aether is licensed under the GNU Affero General Public License v3.0 only. See [`LICENSE`](LICENSE) for details.
