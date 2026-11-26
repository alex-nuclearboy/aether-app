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

The project maintains one shared gettext catalogue per translated language:
``locale/uk/LC_MESSAGES/django.po`` and
``locale/pl/LC_MESSAGES/django.po``. Both have matching compiled ``django.mo``
files. English (UK) is the source language and does not require an additional
project catalogue. Identical ``msgid`` values are translated once for all
modules, unless a distinct gettext context is used. Django's built-in
translations remain available for framework validation messages.

These catalogues cover messages currently extracted from marked source strings;
this does not establish that every user-facing English literal has been marked
or that all translations have completed linguistic review.

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
time through the compiled project catalogues. Django's
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
translation context. Email subjects and bodies can be translated when rendered with an active
translation context. Background workers currently use their own active
language, not a language saved when the recipient requested the email.
Do not claim per-recipient email localisation until the queue language policy
and worker language activation are implemented and tested.

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
request view. The shared project catalogues include the currently marked
validation and feedback messages; newly introduced strings must also be
extracted, translated and tested.

Maintaining the project translation catalogues
-----------------------------------------------

The ``django.po`` files are editable translation sources; their ``django.mo``
counterparts are generated binaries used at runtime. Do not create separate
catalogues for ``accounts`` and ``core``: both applications use the shared
project ``LOCALE_PATHS``. Do not install Babel or a Django translation plugin.

On Windows, GNU gettext is an **external development tool**, not a Python
project dependency. Install it in Windows and ensure ``xgettext``,
``msgmerge``, ``msguniq`` and ``msgfmt`` are on ``PATH``. The standard Django
workflow is run from the repository root (``E:\Projects\aether-app`` on
the current Windows development machine)::

   uv run python manage.py makemessages -l uk -l pl --ignore=".venv/*" --ignore="docs/_build/*"

``makemessages`` extracts strings marked by gettext or the Django template
translation tags, updates the shared ``django.po`` files and preserves
matching translations where possible. It does **not** translate strings.
Review new and obsolete entries, ``fuzzy`` flags, plural forms, placeholders
and ``msgstr`` fields. Maintain accurate catalogue headers, including
``Language``, without changing ``msgid`` values independently of source code.

After reviewing and translating both files, compile the catalogues::

   uv run python manage.py compilemessages -l uk -l pl

Then run the Django checks and automated tests::

   uv run python manage.py check
   uv run pytest

Restart the development server and check pages in all three languages.
Commit the edited ``.po`` files and regenerated ``.mo`` files together.
If Git ignores an untracked ``.mo`` file, add it explicitly with
``git add -f locale/uk/LC_MESSAGES/django.mo locale/pl/LC_MESSAGES/django.mo``;
already tracked compiled files can be updated normally.

Only marked messages are extracted. A separate review must identify any
unmarked user-facing strings; the asynchronous verification and password
reset workers also need explicit language persistence and tests.

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
Direct ``translation.override(...)`` is useful for testing email rendering
outside middleware, but does not prove language persistence in queued work.
``tests/test_language_switch.py`` covers cookie persistence, CSRF, safe
redirects, account routes and authenticated sessions;
``tests/test_settings_i18n.py`` covers settings and middleware ordering.
The tests above do not by themselves guarantee that every extracted source
message has a non-empty, correct translation.
