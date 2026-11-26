Internationalisation and translation
====================================

Current scope
-------------

Aether supports three selectable request languages:

* ``en-gb`` — English (UK), the default;
* ``uk`` — Українська;
* ``pl`` — Polski.

``LANGUAGES`` and ``LOCALE_PATHS`` are configured in ``config/settings.py``.
``LocaleMiddleware`` runs after ``SessionMiddleware`` and before
``CommonMiddleware``. The shared header uses Django's CSRF-protected
``POST /i18n/setlang/`` view. Selecting a language automatically submits the
form through ``static/js/language-switch.js``, without an additional button
when JavaScript is enabled. A ``<noscript>`` ``Apply`` button provides a
non-JavaScript fallback. Django stores the choice in its language cookie.
The choice is browser-specific, not a database-backed user preference.
A localised request does not sign a user out.

Existing account and token URLs are deliberately **not** prefixed with a
language. There is no ``i18n_patterns`` wrapper around ``accounts.urls``.

**Language selection does not mean full translation yet.** Aether's own
interface messages are already marked for translation but the Ukrainian and
Polish project catalogues are not included in this infrastructure step.
Django may display its own framework messages in those languages. Complete
project catalogues, email language persistence and translations are separate
steps that must be implemented and tested before claiming a fully translated
interface.

Python strings
--------------

Use ``gettext_lazy`` for declarations evaluated outside a request: model
field names, help text, validation messages, constraints, form field labels,
and class-level ``error_messages``. In these modules the conventional alias
is ``_``::

   from django.utils.translation import gettext_lazy as _

Use ``gettext`` at request-handling or email-creation time for feedback
messages, HTTP response bodies, and email subjects::

   from django.utils.translation import gettext as _

The login/logout messages, Axes HTTP 429 response, and registration
rate-limit responses use the active request language at response creation
time once their translations are available. Django's
``AuthenticationForm`` and password validators retain their native lazy
translation behaviour.

Do **not** translate internal logging formats, audit event names, database
settings validation, or technical exception messages: these are operational
interfaces, not user-facing copy.

Templates and email
-------------------

Load ``i18n`` and use ``{% trans %}`` for interface text, page titles,
button labels, navigation, ARIA labels, and visible email copy.
``{% blocktrans %}`` is appropriate for phrases with placeholders or
pluralisation. Brand names (``Aether``), CSS classes, URL names, form field
identifiers, and user-supplied content are not translated.

``templates/base.html`` and the verification and password-reset email HTML
templates use
``{% get_current_language as CURRENT_LANGUAGE %}`` to populate the HTML
``lang`` attribute. This keeps document metadata aligned with the active
translation context. Email bodies and subjects currently use the worker's
active language, not a persisted recipient preference. Do not claim
translated worker emails
until the outbox language policy and translation catalogues are implemented.

The existing field component renders labels and validation messages supplied
by Django forms. Do not hard-code replacements for the standard validation
messages, including password policy errors. If customised error presentation
is needed, preserve ``ValidationError`` codes and parameters so that
localisation and testing are not tied to English text.

Registration form validation
----------------------------

``AetherRegistrationForm`` inherits Django's ``UserCreationForm`` so standard
password messages, confirmation errors, and username validation are handled
through Django's own translated validation framework. The custom duplicate
email check and transactional uniqueness-race handler reuse the lazy
``User.email`` and ``User.username`` model field messages with error code
``unique``. These errors remain attached to the corresponding form fields.

Test error codes and field placement rather than hard-coded English wording.
The staged registration result and password-reset pages mark their titles,
queue-status guidance and links with ``{% trans %}``. Profile feedback for
queued, already queued, cooldown and verified states uses ``gettext`` in the
request view. Complete Ukrainian and Polish catalogues must include these
project-defined validation and feedback messages.

Building project translation catalogues
---------------------------------------

The project ``locale/`` directory is now configured. For the next step,
extract the Aether messages to editable catalogues from the project root::

   uv run python manage.py makemessages -l uk
   uv run python manage.py makemessages -l pl

Review and translate each ``msgstr`` in the resulting ``django.po`` files,
including plural forms. Translation files are human-reviewed project
artifacts, not machine-generated truth. Compile them with::

   uv run python manage.py compilemessages

Extraction and compilation require GNU gettext utilities (including
``xgettext`` and ``msgfmt``). Source ``.po`` files should be committed;
compiled ``.mo`` files are ignored by the existing ``.gitignore``.

In the following step, account for asynchronous verification and password
reset emails by recording a language preference alongside queued work.
That change must be designed against the current workers and any required
migration must be generated through Django.

Verification
------------

``accounts/tests/test_interface_translations.py`` tests lazy translation
markers for forms/models and runtime translation of user-visible HTTP and
feedback messages. ``tests/test_template_translations.py`` checks the active
HTML language and translation markers in shared interface templates.

HTTP language tests use request headers and Django's language cookie.
Direct ``translation.override(...)`` remains useful for rendering email
templates outside middleware. ``tests/test_language_switch.py`` covers
cookie persistence, CSRF, allowed hosts, account routes and authenticated
sessions; ``tests/test_settings_i18n.py`` covers settings and middleware
ordering.
