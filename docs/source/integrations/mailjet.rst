Mailjet
=======

Role in Aether
--------------

Mailjet is the currently selected production email delivery provider for
Aether.

The application email verification service uses the default Django mailer.
It delivers both plain-text and HTML messages. Public registration will reuse
this service when implemented.

Aether connects to Mailjet through Django's standard SMTP backend rather than
through a Mailjet-specific SDK or API integration. The application therefore
exposes a provider-neutral SMTP configuration, while this page records the
Mailjet-specific values and operational requirements of the selected
production email configuration.

Replacing Mailjet with another compatible SMTP provider should normally require
changes to deployment configuration and provider documentation rather than to
application email-sending code.

Runtime behaviour
-----------------

Development and test environments use Django's console email backend and do
not contact Mailjet.

Production uses Django's SMTP backend through the ``default`` entry in the
Django ``MAILERS`` setting.

The production connection uses explicit TLS.

SMTP configuration
------------------

The current Aether Mailjet SMTP configuration uses:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Setting
     - Value
   * - SMTP server
     - ``in-v3.mailjet.com``
   * - SMTP port
     - ``587``
   * - Connection security
     - Explicit TLS
   * - SMTP username
     - Mailjet API Key
   * - SMTP password
     - Mailjet Secret Key

The corresponding Aether environment variables are:

.. code-block:: text

   DJANGO_DEFAULT_FROM_EMAIL=<verified sender address>
   MAILER_SMTP_HOST=in-v3.mailjet.com
   MAILER_SMTP_PORT=587
   MAILER_SMTP_USERNAME=<Mailjet API Key>
   MAILER_SMTP_PASSWORD=<Mailjet Secret Key>
   MAILER_SMTP_TIMEOUT=10

``MAILER_SMTP_USERNAME`` and ``MAILER_SMTP_PASSWORD`` are production
credentials and must not be committed to the repository or added to
``.env.example``.

The actual deployment-platform mapping will be documented with the production
deployment configuration.

Sender verification
-------------------

Mailjet requires the sender address or sending domain to be verified before it
can be used for outgoing email.

The current Aether setup uses an individually verified sender address. The
production value of ``DJANGO_DEFAULT_FROM_EMAIL`` must correspond to a sender
accepted by the Mailjet account.

The verified production sender is deployment configuration and is not required
in the local ``.env.example``. Local development instead uses the synthetic
``aether@example.com`` address with Django's console backend.

Domain authentication and deliverability
-----------------------------------------

The current sender domain is not controlled by Aether, so Aether cannot add
Mailjet-specific DNS records for that domain.

This means the current sender setup should be treated as an interim
email-delivery configuration. When Aether uses a dedicated sending domain,
the sending domain should be verified in Mailjet and the appropriate SPF and
DKIM records should be configured before it becomes the preferred production
sender.

Mailjet also warns that sender addresses using free email services can have
reduced deliverability, including a greater likelihood of messages being placed
in spam or rejected. The current individually verified sender should therefore
be treated as an interim configuration rather than the long-term production
sender.

Domain authentication improves sender authentication and deliverability and
reduces the likelihood that legitimate messages are treated as spam.

Secrets
-------

Treat the Mailjet API Key and Secret Key as production credentials.

They must:

* be stored in the deployment platform's secret storage;
* never be added to ``.env.example``;
* never be committed to Git;
* never be written to application logs or documentation;
* be rotated if they are exposed.

See :doc:`../security/secrets` for the general project secret-handling policy.

Verification
------------

The SMTP credentials and verified sender have been tested independently against
Mailjet before being introduced into the Aether settings.

Application-level automated tests use synthetic SMTP values and never connect
to Mailjet. This keeps the test suite deterministic and prevents CI from
depending on external email delivery.

Production delivery should be verified again after the deployment environment
has been configured.

Official references
-------------------

The current provider documentation is available from:

* `Mailjet SMTP parameters`_;
* `Mailjet sender verification`_;
* `Mailjet SPF and DKIM authentication`_.

.. _Mailjet SMTP parameters:
   https://documentation.mailjet.com/hc/en-us/articles/360043229473-How-can-I-configure-my-SMTP-parameters
.. _Mailjet sender verification:
   https://documentation.mailjet.com/hc/en-us/articles/360042759253-How-to-add-a-sender-address
.. _Mailjet SPF and DKIM authentication:
   https://documentation.mailjet.com/hc/en-us/articles/360049641733-Authenticating-Domains-with-SPF-and-DKIM-A-Complete-Guide
