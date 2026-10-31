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
* shared client IP resolution with environment-specific proxy handling
  and IPv4/IPv6 normalisation;
* PostgreSQL access through Psycopg 3;
* PostgreSQL 18 for local development through Docker Compose;
* dependency and virtual-environment management through ``uv``;
* a project-specific Django user model provided by the ``accounts`` application,
  with explicit username syntax, mandatory validated email on managed account
  creation, and PostgreSQL constraints for non-blank email addresses and
  case-insensitive username and email uniqueness;
* a validated public-registration form and transactional account-creation
  service, with case-insensitive identifier checks, standard Django password
  rules, and PostgreSQL uniqueness-race handling (public GET preview only;
  POST account creation remains disabled);
* persistent per-account email verification state, initially unverified and
  matched against the current email independently from account activation;
* a per-account sign-in policy that requires current email verification only
  for accounts explicitly marked as requiring it, without changing Django's
  ``is_active`` semantics or existing Admin/CLI account access;
* synchronous and asynchronous authentication by username or email with
  case-insensitive lookups, using Django's standard password and permissions
  mechanisms;
* PostgreSQL-backed brute-force protection through django-axes, with a
  three-failure threshold, a 15-minute lockout, and shared username/email
  failure counters;
* application sign-in and sign-out using Django's session authentication,
  a neutral username-or-email form, CSRF protection, and safe redirects;
* server-generated request IDs for correlating HTTP and application logs;
* authentication auditing for successful logins, logouts, and lockouts,
  including client IP addresses and protected account identifiers;
* database-backed lockout deadline and remaining-time calculations,
  with UTC deadlines available for future authentication interfaces;
* a read-only authenticated account profile, CSRF-protected email
  verification requests, multipart confirmation messages, a PostgreSQL-backed
  send cooldown, and a public POST-only email confirmation action;
* a ``core`` Django application providing a public home page with the
  full Aether logo;
* a shared base template with a fixed header, clickable brand link,
  and session-aware sign-in/sign-out controls;
* translation-ready Python feedback and template labels, with active-language
  HTML metadata; the application still uses one configured language without
  a language switch or project translation catalogs;
* shared Django form-field markup, reusable button and input styling,
  centralised light-only design tokens, and mobile-first responsive gutters;
* page-specific CSS, brand images, favicons, and Google Fonts typography;
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
* GitHub Actions for continuous quality, Python compatibility, Django
  deployment, and dependency-security checks.

The application layer is intentionally minimal at this stage. Product domains,
service boundaries, background work, and external-provider adapters should be
documented when they are introduced rather than being assumed in advance.

Confirmed platform direction
----------------------------

The planned production target is Koyeb for the Django application and Neon for
managed PostgreSQL. Production deployment has not yet been implemented.

Mailjet is the currently selected provider for production email delivery. Aether
is configured to use Mailjet through the provider-neutral SMTP configuration
documented in :doc:`../integrations/mailjet`.

Google Calendar, external APIs, and cloud-backed file storage remain confirmed
future integration areas. Their concrete architecture, permissions, synchronisation
behaviour, and provider-specific configuration will be documented alongside
the corresponding implementation.
