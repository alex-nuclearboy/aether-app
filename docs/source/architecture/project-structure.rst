Project structure
=================

Aether is still at an early stage, so the repository is intentionally small.
The current structure contains the Django project configuration, local
development infrastructure, automated tests, documentation, and code-quality
tooling.

Application-specific Django apps, integrations, and service layers will be
added as the corresponding functionality is implemented rather than being
created in advance. Tests that belong to those components should be introduced
together with the code they verify.

Current structure
-----------------

The repository currently has the following top-level structure:

.. code-block:: text

   aether-app/
   ├── .github/
   │   └── workflows/
   │       └── code-quality.yml
   ├── config/
   │   ├── __init__.py
   │   ├── asgi.py
   │   ├── settings.py
   │   ├── urls.py
   │   └── wsgi.py
   ├── docs/
   │   ├── source/
   │   │   ├── architecture/
   │   │   ├── deployment/
   │   │   ├── development/
   │   │   ├── getting-started/
   │   │   ├── integrations/
   │   │   ├── reference/
   │   │   ├── security/
   │   │   ├── conf.py
   │   │   └── index.rst
   │   ├── Makefile
   │   ├── make.bat
   │   └── README.md
   ├── tests/
   │   ├── __init__.py
   │   ├── test_database.py
   │   ├── test_django_entrypoints.py
   │   └── test_settings.py
   ├── .env.example
   ├── .gitignore
   ├── .python-version
   ├── compose.yaml
   ├── LICENSE
   ├── manage.py
   ├── pyproject.toml
   ├── README.md
   └── uv.lock


Django project configuration
----------------------------

``config/``
~~~~~~~~~~~

The ``config`` package contains the project-level Django configuration.

It is responsible for settings, root URL routing, and the WSGI and ASGI
application entry points. Application-specific code should not normally be
placed here.

``config/settings.py``
~~~~~~~~~~~~~~~~~~~~~~

The main Django settings module.

The file currently handles:

* environment-variable loading;
* validation of required configuration;
* Django security settings;
* installed applications and middleware;
* PostgreSQL configuration;
* database connection settings;
* password validation;
* internationalisation;
* static files;
* email backend configuration.

Configuration is environment-driven. Local development values are loaded from
``.env``, while deployment environments can provide their own environment
variables.

Database URLs are validated before being converted into Django database
settings. Aether currently requires PostgreSQL rather than supporting multiple
database backends.

For a detailed explanation of the configuration model, see
:doc:`configuration`.

For the complete environment-variable reference, see
:doc:`../reference/environment-variables`.

``config/urls.py``
~~~~~~~~~~~~~~~~~~

Defines the root URL configuration for the Django project.

At the current stage, it exposes the Django administration interface. Routes
for application-specific functionality will be included here or delegated to
individual Django apps as the project grows.

``config/asgi.py``
~~~~~~~~~~~~~~~~~~

Exposes the ASGI application used by ASGI-compatible application servers.

Keeping the ASGI entry point available allows the deployment architecture to
support asynchronous Django capabilities if they are required later.

``config/wsgi.py``
~~~~~~~~~~~~~~~~~~

Exposes the WSGI application used by WSGI-compatible application servers.

The final production server configuration will be documented together with
the Koyeb deployment setup once deployment is introduced.

``config/__init__.py``
~~~~~~~~~~~~~~~~~~~~~~

Marks ``config`` as a Python package.

It intentionally contains no project configuration.


Project entry point
-------------------

``manage.py``
~~~~~~~~~~~~~

The command-line entry point for Django administrative tasks.

Common commands include:

.. code-block:: console

   uv run python manage.py check
   uv run python manage.py makemigrations
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   uv run python manage.py runserver

The full command reference is available in
:doc:`../reference/commands`.


Dependency and Python configuration
-----------------------------------

``pyproject.toml``
~~~~~~~~~~~~~~~~~~

Defines the Python project metadata and dependency configuration used by
``uv``.

It contains:

* project metadata;
* supported Python versions;
* runtime dependencies;
* development dependencies;
* ``uv`` configuration;
* pytest and coverage configuration;
* Pylint configuration.

Runtime dependencies are packages required by the application itself.
Development-only tools such as pytest, pytest-django, pytest-cov, Pylint, and
Sphinx belong to the development dependency group.

``uv.lock``
~~~~~~~~~~~

The lock file generated and maintained by ``uv``.

It records the exact resolved dependency graph so that local development and
continuous integration use reproducible package versions.

The file is committed to the repository and should normally be updated through
``uv`` rather than edited manually.

``.python-version``
~~~~~~~~~~~~~~~~~~~

Defines the preferred Python version for local development.

The project may support more than one Python version, while this file provides
a consistent default for developers and tooling that understand
``.python-version`` files.


Environment configuration
-------------------------

``.env.example``
~~~~~~~~~~~~~~~~

Documents the environment variables required or supported by the project.

It contains safe example values and placeholders only. It must never contain
real development or production credentials.

For local development, the file is copied to ``.env`` and the required secret
values are filled in locally.

The current template includes configuration for:

* the Django secret key;
* debug mode;
* allowed hosts;
* the local PostgreSQL instance;
* ``DATABASE_URL``;
* database connection behaviour;
* language and time zone settings.

The complete description of each variable is maintained in
:doc:`../reference/environment-variables`.

``.env``
~~~~~~~~

The local environment file.

It is created from ``.env.example`` during local setup and is intentionally
excluded from version control because it may contain credentials and other
machine-specific values.

Production environments do not rely on the repository's local ``.env`` file.
Deployment configuration and secrets are supplied through the hosting
environment instead.


Local PostgreSQL infrastructure
-------------------------------

``compose.yaml``
~~~~~~~~~~~~~~~~

Defines the Docker Compose service used for the local PostgreSQL database.

The configuration currently provides:

* PostgreSQL 18;
* environment-based database name, user, and password;
* a host-only PostgreSQL port binding;
* persistent storage through a named Docker volume;
* a PostgreSQL health check.

Docker Compose is part of the local development environment only. The planned
production environment uses managed PostgreSQL instead.

See :doc:`../development/database` for the local database workflow and
:doc:`../deployment/index` for the current production direction.

Testing
-------

``tests/``
~~~~~~~~~

Contains project-level automated tests for configuration, infrastructure, and
Django project entry points.

The current package contains:

``tests/test_settings.py``
   Tests environment handling, PostgreSQL configuration, database URL
   expansion, validation paths, connection options, and module-level settings
   behaviour.

``tests/test_database.py``
   Contains integration tests that verify PostgreSQL as the configured database
   backend and execute queries through Django's database connection.

``tests/test_django_entrypoints.py``
   Contains smoke tests for the ASGI application, WSGI application, and root
   URL configuration.

``tests/__init__.py``
   Marks the root test directory as a Python package.

The root ``tests/`` package is intended for project-wide configuration and
infrastructure tests. Tests that belong to a specific Django application should
normally live inside that application's own ``tests/`` package.

Aether uses ``pytest`` and ``pytest-django`` for test execution and
``pytest-cov`` for statement and branch coverage.

See :doc:`../development/testing` for the testing strategy, PostgreSQL test
database behaviour, coverage policy, and supported test commands.

Continuous integration
----------------------

``.github/workflows/code-quality.yml``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the GitHub Actions workflow used for automated project checks.

The workflow currently:

* checks out the repository;
* configures Python;
* installs ``uv``;
* validates the lock file;
* installs project and development dependencies;
* starts a temporary PostgreSQL service;
* runs Django system checks;
* checks for missing migrations;
* applies committed migrations;
* runs the automated test suite with coverage enforcement;
* runs Pylint;
* builds the Sphinx documentation in strict mode.

The automated tests use the temporary PostgreSQL service provided by the
workflow. The same coverage policy defined in ``pyproject.toml`` applies both
locally and in continuous integration.

The CI database is temporary and exists only for the duration of the workflow.

See :doc:`../development/continuous-integration` for the detailed CI workflow.


Documentation
-------------

``docs/``
~~~~~~~~~

Contains the Sphinx documentation project.

The documentation is intentionally separated from the root ``README.md``.
The README provides a concise project introduction and quick-start workflow,
while Sphinx contains the detailed development, architecture, deployment,
security, and reference documentation.

The directory contains:

.. code-block:: text

   docs/
   ├── source/
   │   ├── architecture/
   │   ├── deployment/
   │   ├── development/
   │   ├── getting-started/
   │   ├── integrations/
   │   ├── reference/
   │   ├── security/
   │   ├── conf.py
   │   └── index.rst
   ├── Makefile
   ├── make.bat
   └── README.md

``docs/source/``
~~~~~~~~~~~~~~~~

Contains the documentation source files.

The documentation is organised by purpose rather than by Python package:

``getting-started/``
   Initial setup and local development onboarding.

``development/``
   Development workflows such as PostgreSQL, automated testing, code quality,
   continuous integration, and documentation maintenance.

``architecture/``
   Explanations of the project structure, configuration model, and architectural
   decisions.

``deployment/``
   Production deployment documentation. This section will expand when the
   Koyeb and Neon environments are implemented.

``integrations/``
   Documentation for external systems such as Google Calendar, external APIs,
   and file-storage providers as those integrations are introduced.

``security/``
   Security-related documentation, including secrets and future authentication
   and OAuth concerns.

``reference/``
   Precise technical reference material such as environment variables and
   commonly used commands.

``docs/source/conf.py``
~~~~~~~~~~~~~~~~~~~~~~~

Contains the Sphinx configuration.

It defines the documentation project metadata and build configuration. The
project version is read from ``pyproject.toml`` so that it does not need to be
duplicated manually in the documentation configuration.

The file is included in the project's Pylint checks.

``docs/source/index.rst``
~~~~~~~~~~~~~~~~~~~~~~~~~

The root page of the Sphinx documentation.

It defines the top-level documentation navigation and links the main
documentation sections together.

``docs/Makefile`` and ``docs/make.bat``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convenience build helpers generated for the Sphinx documentation.

The documentation can also be built directly with ``sphinx-build``. See
:doc:`../development/documentation` for the supported build commands.

``docs/_build/``
~~~~~~~~~~~~~~~~

Contains generated Sphinx output.

This directory is generated locally or in CI and is excluded from version
control.


Repository documentation
------------------------

``README.md``
~~~~~~~~~~~~~

The main entry point for the repository.

It provides:

* a concise description of Aether;
* local requirements;
* the quick-start workflow;
* essential development and test commands;
* documentation build instructions;
* the current deployment direction.

Detailed technical explanations belong in the Sphinx documentation rather than
being duplicated in the README.

``LICENSE``
~~~~~~~~~~~

Contains the GNU Affero General Public License version 3 under which Aether is
distributed.


Version-control configuration
-----------------------------

``.gitignore``
~~~~~~~~~~~~~~

Defines files and directories that must not be committed.

This includes local environments, generated Python files, local credentials,
database artefacts, documentation build output, and development-tool caches.


Generated and local-only files
------------------------------

Several files and directories may exist in a local checkout without appearing
in the repository.

Important examples include:

``.env``
   Local environment configuration and credentials.

``.venv/``
   The local Python virtual environment managed by ``uv``.

``docs/_build/``
   Generated Sphinx documentation.

``.pytest_cache/``
   Local pytest cache generated during test execution.

``__pycache__/``
   Generated Python bytecode cache directories.

``.coverage``
   Local coverage data generated while running the automated test suite.

Docker volumes
   Persistent PostgreSQL data managed by Docker rather than stored inside the
   repository.

These artefacts are deliberately kept outside version control.


Future growth
-------------

The current structure should expand only when corresponding functionality is
introduced.

Expected areas include Django applications for the product domain, service
layers, external integrations, and provider-specific infrastructure.
Application-specific test packages should be introduced alongside the
components they verify.

The final package structure should be driven by implementation needs rather
than by creating placeholder modules in advance.

The architecture documentation should be updated whenever a structural change
introduces a new long-lived project component.
