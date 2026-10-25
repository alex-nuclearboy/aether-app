Frontend structure and responsive design
========================================

Aether uses Django templates and plain CSS. Reusable layout and form markup
is kept separate from page-specific templates. No additional CSS framework,
JavaScript build system, or theme-switching mechanism is required.

Shared templates
----------------

``templates/base.html`` defines the document and stylesheet order. Shared
navigation stays in ``templates/includes/header.html``. Form controls with
identical markup use ``templates/components/form_field.html`` via Django's
``include`` tag. Application-specific pages remain in their Django app,
including ``accounts/templates/accounts/login.html``.

Do not create a template partial for a simple button: use the shared CSS
``button`` classes on a native ``button`` or ``a`` element. Add a new
component template only when markup is repeated or accessibility requires
consistent internal structure.

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

The application sign-in page uses a dedicated, centred layout without the
shared site header. It retains the base document, shared form-field partial,
stylesheets, CSRF protection, and Django authentication behaviour. No social
login, registration, or password-reset links are displayed because these
features are not implemented.

Status colours and flash messages
---------------------------------

Semantic success, information, warning, and error values are defined in
``static/css/foundations/tokens.css``. Components consume these values rather
than duplicating palette literals. Shared ``alert.css`` styles the severity
classes used by ``templates/components/messages.html``.

Django's messages framework renders one-time feedback after a redirect. The
application logout adds a success message, displayed once on the destination
page. The existing form validation errors and HTTP 429 response behaviour
remain separate from this flash-message mechanism.
