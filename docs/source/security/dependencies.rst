Dependency security
===================

Aether automatically audits its Python dependency graph for publicly known
vulnerabilities and adverse package statuses.

Dependency auditing complements, but does not replace, application-level
security controls, Django deployment checks, secret management, or security
review of application code.


Audit tool
----------

Dependency auditing uses ``uv audit`` against the committed ``uv.lock`` file.

For a local audit of the current environment::

   uv audit --preview-features audit-command --locked

The command requires network access.

``uv audit`` is currently a preview feature. CI explicitly enables the
``audit-command`` preview feature so that use of the experimental interface is
intentional and visible in the workflow configuration.


Supported Python versions
-------------------------

Aether currently supports Python 3.12, 3.13, and 3.14.

Continuous integration audits the dependency graph separately for each of
these Python versions on Linux. This matters because environment markers and
transitive dependency selections may differ between Python versions even when
the same ``uv.lock`` file is used.

The ``--python-version`` option selects the dependency graph to audit. It does
not require ``uv`` itself to run under that Python interpreter.


Audit scope
-----------

By default, ``uv audit`` evaluates the project's dependency groups and extras,
including development dependencies.

This means that development tooling is also covered by the automated security
check rather than only packages required by the production application.

The audit currently checks dependency metadata for known vulnerabilities and
adverse project statuses. It does not analyse Aether's own source code for
security defects.


CI behaviour
------------

The ``security`` job in ``.github/workflows/code-quality.yml`` audits:

* Python 3.12 on Linux;
* Python 3.13 on Linux;
* Python 3.14 on Linux.

The job does not start PostgreSQL and does not require the Django CI
environment because it operates on the locked dependency graph.

A reported vulnerability or adverse dependency status causes the corresponding
audit step to fail.

See :doc:`../development/continuous-integration` for the complete workflow.
