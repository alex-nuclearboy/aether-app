Integrations
============

Aether keeps provider-specific integration details separate from the core
application configuration. The Django settings expose provider-neutral
interfaces where possible, while integration documentation records the
configuration and operational requirements of the selected external service.

Implemented integrations
------------------------

* :doc:`mailjet` — production email delivery through SMTP.

Planned areas
-------------

Current planned areas include:

* Google Calendar;
* external APIs;
* cloud-backed file storage;
* OAuth-based provider access where required;
* scheduled and automated operations.

Integration documentation should record authentication and permissions,
configuration, data ownership, synchronisation behaviour, failure handling,
provider limits, and the boundary between provider-specific services and the
Aether core.

Provider choices and API contracts should not be documented as final before
they are implemented and verified.

.. toctree::
   :maxdepth: 1
   :hidden:

   mailjet
