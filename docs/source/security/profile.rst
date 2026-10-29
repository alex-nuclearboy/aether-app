Profile and email verification
==============================

Scope
-----

The authenticated account profile is available at ``/profile/``. The page
shows the current username and email address and the computed
``is_email_verified`` status. It is deliberately read-only: changing email,
username, password, and other account details will be introduced separately.
No public registration UI is provided at this stage.

The shared header links to the profile only for authenticated users.
Django Admin retains its standard appearance and account management UI.

Email delivery
--------------

An unverified user may submit a CSRF-protected POST request to
``/profile/verify-email/`` to request a verification message. The endpoint
never accepts a recipient address from the browser: it reloads the account
from PostgreSQL and uses its current ``email`` field. It does not send
verification messages to addresses that are already confirmed.

``accounts.emails.send_verification_email`` creates a token using the existing
``accounts.tokens.email_verification_token`` generator and constructs an
absolute confirmation URL. Text and HTML message bodies are rendered from
Django templates, and ``EmailMultiAlternatives`` sends both alternatives
through the existing default ``MAILERS`` backend. Local development uses the
console backend; production uses the configured SMTP provider (Mailjet).

One delivery reservation per account is permitted in any 60-second window.
The ``User.email_verification_sent_at`` timestamp is stored in PostgreSQL and
checked under ``select_for_update()`` within an atomic transaction. The row
lock is released before SMTP delivery, avoiding network I/O inside the
transaction. A failed send clears only its own reservation, allowing a retry.
The timestamp is account-level; it does not represent a verified email.

Link confirmation
-----------------

The link targets ``/email/verify/<uidb64>/<token>/``. An unauthenticated
recipient may open the confirmation page, so the same endpoint can later be
used by public registration. GET only validates the link and displays a form.
A CSRF-protected POST calls the existing ``verify_email()`` service, which
re-reads the user with a PostgreSQL row lock and records the current address
in ``verified_email``. Previously consumed, expired, malformed, or stale
links cannot confirm an email address.

The response redirects to ``/email/verification-result/`` after POST so the
token is removed from the visible browser address. Verification pages are not
cached and set ``Referrer-Policy: origin``. The project's HTTP request
logger masks the user identifier and token in confirmation paths rather than
writing the link into application logs. Reverse proxies and hosting access
logs should also be configured not to record these sensitive paths.

Confirming an email address never changes ``is_active``, permissions, or the
user's authenticated session. Existing accounts created through Django Admin
or ``createsuperuser`` may continue to sign in while unverified, as previously
agreed. Restricting login during future public registration is a separate
account lifecycle concern and is not implemented here.

Future account changes
----------------------

The verification state is intentionally tied to the **current** email
address: ``is_email_verified`` compares ``email`` with ``verified_email``.
Changing the email address in a future profile-editing workflow therefore
invalidates the verified status without requiring a second boolean flag.
That future editing service must also clear ``verified_email`` on a genuine
address change so returning to an old address cannot restore confirmation
implicitly. Editing forms will be separate POST views with appropriate
validation and reauthentication checks; the present read-only profile does
not anticipate or expose any such form.

The shared email-sending service and the public confirmation endpoint can be
reused by the future registration workflow. Registration-specific account
activation or pending-registration state must be designed independently of
``is_active`` and ``verified_email``.
