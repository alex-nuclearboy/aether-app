Profile and email verification
==============================

Scope
-----

The authenticated account profile is available at ``/profile/``. The page
shows the current username and email address and the computed
``is_email_verified`` status. It is deliberately read-only: changing email,
username, password, and other account details will be introduced separately.
Registration POST is available only when the development/test flag is
enabled. Authenticated users can request verification from their profiles;
public registration remains disabled in production. Public email resend and
pre-verification correction are available independently of the registration
gate. Neither route grants a signed-in session or edits a verified profile.

The shared header links to the profile only for authenticated users.
Django Admin retains its standard appearance and account management UI.

Email delivery
--------------

An unverified user may submit a CSRF-protected POST request to
``/profile/verify-email/`` to request a verification message. The endpoint
never accepts a recipient address from the browser: it reloads the account
from PostgreSQL and uses its current ``email`` field. It does not send
verification messages to addresses that are already confirmed.

``accounts.email_outbox.queue_verification_email()`` stores a pending
``VerificationEmailJob`` in PostgreSQL without contacting SMTP. The job stores
the intended recipient, not a verification token or rendered message.
``accounts.email_worker`` generates the token and renders plain-text and HTML
bodies immediately before delivery. It uses Django's configured ``MAILERS``
backend: the console backend locally and SMTP (Mailjet) in production.
Before constructing a message, the worker cancels a queued job if the
account is inactive. This does not change account activation or email
verification state. Deactivation after this check may still overlap with
SMTP delivery already in progress.

The user row is locked while the job and account-level
``email_verification_sent_at`` timestamp are saved in one transaction.
An already active job for the same account and recipient is not duplicated.
After a job has completed, the timestamp enforces a 60-second cooldown between
requests. Transport failures and unexpected token, template or mail-backend
errors are retried with bounded delays and at most five attempts. Only a
non-sensitive error category is stored; exception messages and generated
verification URLs are never saved in the job. These errors do not clear the
original reservation. This timestamp does not represent verified ownership.

Verification link origin
------------------------

The worker builds verification URLs from the explicit trusted
``--public-origin`` argument and the generated confirmation path, not from
incoming ``Host`` headers or ``request.build_absolute_uri()``. Development
may use ``http://127.0.0.1:8000``; production requires a verified public HTTPS
origin. Check the link in both the plain-text and HTML message bodies.

Production proxy and client-IP settings require a separate deployment review.
The worker origin setting does not establish trust in forwarded HTTP headers.

Link confirmation
-----------------

The link targets ``/email/verify/<uidb64>/<token>/``. An unauthenticated
recipient may open the confirmation page. The staged registration workflow
reuses this endpoint. GET only validates the link and displays a form.
A CSRF-protected POST calls the existing ``verify_email()`` service, which
re-reads the user with a PostgreSQL row lock and records the current address
in ``verified_email``. Previously consumed, expired, malformed, or stale
links cannot confirm an email address.

The response redirects to ``/email/verification-result/`` after POST so the
token is removed from the visible browser address. Verification pages are not
cached and set ``Referrer-Policy: origin``. The project's HTTP request
logger masks the user identifier and token in confirmation paths, including
requests redirected before URL resolution and malformed confirmation paths.
This is specific to the ``aether.http`` logger; Django diagnostics, reverse
proxies and hosting access logs require separate protection against sensitive
paths.

Confirming an email address never changes ``is_active``, permissions, or the
user's authenticated session. Existing accounts created through Django Admin
or ``createsuperuser`` may continue to sign in while unverified, as previously
agreed. Accounts with ``email_verification_required=True`` cannot sign in
until their current email is verified. This policy is enforced in the
username-or-email backend and is independent of ``is_active``.

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

Staged registration POST creates the unverified account and its outbox job
in the same transaction, without changing ``is_active``. If enqueuing fails,
the account creation is rolled back. The result page confirms queuing, not
SMTP acceptance or final delivery. The worker handles delivery failures and
retries separately. Registration POST already has a per-IP request limit;
public resend and pre-verification correction are implemented with neutral
responses and separate rate limits. Production registration nevertheless
remains disabled pending deployment and security safeguards.
