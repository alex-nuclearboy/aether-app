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


Dependabot security monitoring
------------------------------

Aether also uses GitHub Dependabot as an independent dependency-security
layer.

Dependabot alerts monitor the dependency graph on the repository's default
branch and report supported dependencies affected by known vulnerabilities.

Malware alerts are also enabled to report dependencies identified as
malicious.

Dependabot security updates are enabled. When a compatible remediation is
available for a vulnerable dependency, Dependabot may create a pull request
containing the security update.

These pull requests are not merged automatically. They are reviewed and pass
through the normal project CI workflow before a maintainer decides whether to
merge them.


Security-only policy
--------------------

Routine Dependabot version updates are intentionally disabled.

Aether does not use Dependabot to automatically propose ordinary package
upgrades merely because newer versions have been released. Non-security
dependency upgrades remain an explicit maintenance decision.

The current policy is therefore:

* dependency graph: enabled;
* automatic dependency submission: disabled;
* Dependabot alerts: enabled;
* malware alerts: enabled;
* Dependabot security updates: enabled;
* grouped security updates: disabled;
* Dependabot auto-triage rules: disabled;
* routine Dependabot version updates: disabled.

Automatic dependency submission is not required for the current Python setup.
GitHub uses Dependabot graph jobs for Python repositories with the dependency
graph enabled, and these jobs take precedence over automatic dependency
submission.

No ``.github/dependabot.yml`` file is required for the current policy.
Dependabot security updates are controlled through the repository's GitHub
security settings.


Relationship to uv audit
------------------------

Dependabot and ``uv audit`` have complementary responsibilities.

``uv audit`` validates the locked dependency graph during continuous
integration and causes CI to fail when known vulnerabilities or adverse
project statuses are detected.

Dependabot monitors the repository dependency graph through GitHub's security
infrastructure and can raise new alerts when vulnerabilities are disclosed
after the dependency versions were committed.

When remediation is available, Dependabot can additionally prepare a security
update pull request.

Using both mechanisms provides continuous repository-level monitoring together
with repeatable CI validation.


Security update workflow
------------------------

A Dependabot security update follows the normal pull-request workflow::

   Vulnerability disclosed
          |
          v
   Dependabot alert
          |
          v
   Security update pull request
          |
          v
   GitHub Actions
          |
          +-- project quality checks
          +-- Python compatibility tests
          +-- dependency audit
          |
          v
   Maintainer review
          |
          v
   Manual merge

Dependabot does not bypass the project's normal quality gates and automatic
merging is not enabled.


Current scope
-------------

The current Dependabot integration primarily covers supported Python
dependencies and GitHub Actions represented in GitHub's dependency graph.

Container-image vulnerability scanning is not part of the current baseline and
will be addressed separately when the production container architecture is
introduced.
