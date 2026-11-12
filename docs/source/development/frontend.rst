Frontend structure and responsive design
========================================

Aether uses Django templates and plain CSS. Reusable layout and form markup
is kept separate from page-specific templates. No additional CSS framework,
JavaScript build system, or theme-switching mechanism is required.

Shared templates
----------------

``templates/base.html`` defines the document and stylesheet order. Shared
navigation stays in ``templates/includes/header.html``. Anonymous users see
``Sign in`` and ``Sign up`` links; authenticated users see ``My profile``
and the POST-only ``Sign out`` button. The registration link is displayed
even when account creation is disabled: the registration page retains its
own submission gate. Form controls with
identical markup use ``templates/components/form_field.html`` via Django's
``include`` tag. Application-specific pages remain in their Django app,
including ``accounts/templates/accounts/login.html``.

Do not create a template partial for a simple button: use the shared CSS
``button`` classes on a native ``button`` or ``a`` element. Add a new
component template only when markup is repeated or accessibility requires
consistent internal structure.

The shared form-field component renders Django's field ``help_text`` and
validation errors. It uses ``<field ID>_helptext`` and ``<field ID>_error``
IDs so Django 6.1 can associate the messages with input widgets using its
built-in ``aria-describedby`` and ``aria-invalid`` attributes. These IDs
must remain aligned if the component markup changes. Password guidance
comes from Django's configured validators; do not duplicate its text.

CSS layers
----------

Styles are loaded in this order:

#. ``static/css/foundations/tokens.css`` – values and viewport adjustments.
#. ``static/css/base.css`` – document defaults, box sizing and focus rules.
#. ``static/css/layout.css`` – common content width and spacing.
#. ``static/css/components/*.css`` – reused UI elements.
#. ``static/css/pages/*.css`` – page-specific layout only.

Global colours are declared as primitive and semantic custom properties.
Components consume semantic properties such as ``--colour-text`` and
``--colour-focus`` rather than repeating hexadecimal values. Use the shared
spacing and radius scales where practical. Page-specific dimensions, such
as the maximum width of the login form, remain with the page.

Responsive viewport ranges
--------------------------

The interface is mobile-first. Viewport ranges are explicit:

.. list-table::
   :header-rows: 1
   :widths: 35 30 35

   * - Viewport width
     - Range
     - Header and horizontal gutter
   * - Below ``640px``
     - Mobile: ``320–639px``
     - ``56px`` header, ``16px`` gutter
   * - ``640–1023px``
     - Tablet
     - ``64px`` header, ``24px`` gutter
   * - ``1024–1439px``
     - Desktop
     - ``64px`` header, ``32px`` gutter
   * - ``1440px`` and wider
     - Wide desktop
     - ``64px`` header, ``40px`` gutter

The first range starts at ``320px`` because that is the tested minimum
layout width, not a restriction on device type. Test actual browser viewport
widths, including the exact boundaries ``639/640``, ``1023/1024`` and
``1439/1440``. Browser zoom, text scaling, landscape orientation, and
keyboard navigation must also remain usable. These CSS rules do not by
themselves prove the layouts are visually correct: check them in a browser.

CSS custom properties cannot substitute for pixel values in ordinary
``@media`` conditions. Therefore the three numeric thresholds are defined
in ``tokens.css`` and described here, while components rely on the resulting
responsive custom properties rather than repeating media queries.

Theme policy
------------

The current interface uses one light appearance. Colour aliases separate
meaning from literal values, but no dark theme, user theme preference,
JavaScript theme switch, or additional palette is implemented at this stage.

Login layout
------------

The application sign-in page uses a dedicated, centred layout within
the shared base template. The fixed site header remains visible.

The page includes its own logo, a sign-in panel, reusable form fields,
and compact validation feedback. Authentication uses Django's standard
session mechanism and CSRF protection.

The sign-in page links to registration, public verification resend,
pre-verification email correction, and ``Forgot your password?`` at
``/password/reset/``. Social sign-in is not implemented.

Registration layout (staged)
----------------------------

``accounts/templates/accounts/register.html`` uses the existing shared form
fields and a separate ``static/css/pages/register.css`` stylesheet, matching
the centred composition of the sign-in page. Username, email, password, and
password confirmation come from ``AetherRegistrationForm``; password help
text and validation messages are supplied by Django. All new interface copy
uses ``{% trans %}``. The action button is disabled and POST returns HTTP 405
unless ``REGISTRATION_ENABLED`` is enabled in development or tests.

When enabled, invalid submissions display field errors in the same form and
successful submissions atomically queue a verification email and redirect
to the token-free ``Check your email`` page
(``accounts/templates/accounts/registration_check_email.html``). The result
page confirms queuing rather than delivery and links to the public resend
form. The separate ``/register/resend/`` page collects an email address and
redirects to a neutral result for unknown and eligible accounts alike.
Neither page exposes recipient details. The separate
``/register/correct-email/`` page allows a never-verified public account
holder to supply their registration username, password and corrected email.
It uses the same shared form components and stylesheet, and redirects to a
neutral result without disclosing account eligibility or sending HTTP SMTP.
Production registration remains disabled.

Password-reset pages
--------------------

``accounts/templates/accounts/password_reset_request.html`` presents a
CSRF-protected email-only form with shared form fields and
``static/css/pages/register.css``. The public page remains available while
new registration is disabled. Valid requests redirect to the neutral
``password_reset_done.html`` page; it confirms only that a reset message
**may** be sent, not that a user or delivery exists.

``password_reset_confirm.html`` presents Django's standard new-password
fields and password validation. A valid token is exchanged by Django on GET
for a session-backed intermediate ``set-password`` URL before the form is
shown; the original bearer token is not retained in the visible form URL.
``password_reset_complete.html`` links back to sign-in without logging the
user in. Both emails have translated plain-text and HTML templates in
``accounts/templates/accounts/email/``. The existing registration stylesheet
is deliberately reused, with no new page-specific CSS layer.

Profile and email verification pages
------------------------------------

``accounts/templates/accounts/profile.html`` is a read-only authenticated
page. Its styles are defined in ``static/css/pages/profile.css``. It reuses
the shared header, buttons, alerts, design tokens, and CSRF support.

The confirmation and result pages use dedicated account templates and
``static/css/pages/email-verification.css``. Email messages have separate
plain-text and HTML templates in ``accounts/templates/accounts/email/``.
Future email-editing forms will be introduced as a separate feature rather
than added to the current read-only profile.

Internationalisation
--------------------

User-visible page titles, navigation, buttons, notifications, and ARIA labels
are marked with Django template ``{% trans %}``. The shared base template
and verification email HTML set their ``lang`` attribute from the active
Django translation language. See :doc:`internationalisation` for Python
message conventions, standard Django validation messages, and the limits
of the current single-language configuration.
