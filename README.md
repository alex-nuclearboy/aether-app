# Aether

[![Code Quality](https://github.com/alex-nuclearboy/aether-app/actions/workflows/code-quality.yml/badge.svg)](https://github.com/alex-nuclearboy/aether-app/actions/workflows/code-quality.yml)

Aether is an early-stage personal digital environment built with Django. It is intended to provide a common layer for organising information, tasks, knowledge, files, integrations, and automation without coupling the core application to a single external service.

The current foundation provides a reproducible development and deployment-oriented setup with environment-based Django configuration, PostgreSQL, Docker Compose, `uv` dependency management, automated testing with pytest, Pylint, Sphinx documentation, and GitHub Actions.

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

Django will prompt you for a username, email address, and password. The superuser account is intended for local administration and development; do not reuse production credentials.

### Run the application

Start the Django development server:

```console
uv run python manage.py runserver
```

The application is available at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

The Django administration site is available at [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/).

To stop the development server, press `Ctrl+C` in the terminal where `runserver` is running. Then stop PostgreSQL with:

```console
docker compose down
```

The named database volume is preserved.

## Development checks

Run the current project checks before committing changes:

```console
uv lock --check
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pylint config manage.py docs/source/conf.py
uv run pytest
uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
```

GitHub Actions runs the core quality checks, automated tests with coverage enforcement, and documentation validation against a temporary PostgreSQL instance for pushes and pull requests targeting `main`.

Additional quality checks, such as dependency auditing, will be introduced as the project grows.

## Documentation

Detailed project documentation lives in [`docs/`](docs/README.md) and is built with Sphinx. It covers development workflows, PostgreSQL, automated testing and coverage, architecture, configuration, CI, security, environment variables, commands, and the confirmed deployment and integration direction.

Build the documentation from the repository root with:

```console
uv run sphinx-build -E -a -W -n -T -b html docs/source docs/_build/html
```

The generated HTML is written to `docs/_build/html/` and is not committed to the repository.

## Deployment direction

The planned production environment uses Koyeb for application hosting and Neon for managed PostgreSQL. Google Calendar, external APIs, and cloud-backed file storage are planned integration areas. Provider-specific instructions will be documented when those parts are implemented and tested.

## License

Aether is licensed under the GNU Affero General Public License v3.0 only. See [`LICENSE`](LICENSE) for details.
