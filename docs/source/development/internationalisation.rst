Internationalisation and translation
====================================

Current scope
-------------

Aether's application-facing strings are marked for translation, but the
application currently operates in one configured language. The default is
``en-gb`` (``DJANGO_LANGUAGE_CODE``). ``USE_I18N`` is enabled. There is no
language switch, ``LocaleMiddleware``, project translation catalog, or
stored user language preference yet. The standard Django Admin remains
unchanged and uses the configured Django language.

Marking a message for translation does **not** translate it into Polish,
Ukrainian, or another language automatically. Django ships translations
for its own standard messages. Aether-specific translations will need
project catalogs when additional languages are introduced.

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

The login/logout success messages and the Axes HTTP 429 response are
translated at response creation time. Django's ``AuthenticationForm`` and
password validators retain their native lazy translation behaviour.

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

``templates/base.html`` and the verification email HTML template use
``{% get_current_language as CURRENT_LANGUAGE %}`` to populate the HTML
``lang`` attribute. This keeps document metadata aligned with the active
translation context. Email bodies and subjects use Django's active language
at the time of sending; they are not yet based on recipient preferences.

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
The current English-only interface is unchanged; future Aether translation
catalogs must include all project-defined account validation messages.

Adding languages later
----------------------

When the application supports more than one language, separately design:

* the supported-language list and language-selection behaviour;
* a persisted user preference or other language selection policy;
* the interaction of ``LocaleMiddleware`` with authentication and the
  standard Django Admin;
* locale catalogs for Aether's own messages, and their compilation.

First create a project ``locale/`` directory and configure
``LOCALE_PATHS = [BASE_DIR / "locale"]`` in ``config/settings.py``.
Then, from the project root, use Django's extraction tools::

   uv run python manage.py makemessages -l pl
   uv run python manage.py makemessages -l uk
   uv run python manage.py compilemessages

These commands require GNU gettext utilities (``xgettext``, ``msgfmt``).
They are **not** required for the present English-only interface. A
translation catalog and actual translated content should be reviewed before
a language is made available to users.

Verification
------------

``accounts/tests/test_interface_translations.py`` tests lazy translation
markers for forms/models and runtime translation of user-visible HTTP and
feedback messages. ``tests/test_template_translations.py`` checks the active
HTML language and translation markers in shared interface templates.

Language override tests use ``translation.override(...)`` to exercise the
mechanism without enabling language switching or requiring a complete
application translation catalog.
