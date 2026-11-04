"""Integration tests for registration, email confirmation and sign-in."""

import re
from urllib.parse import urlsplit

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from accounts.email_worker import (
    DeliveryOutcome,
    deliver_next_verification_email,
)
from accounts.models import User, VerificationEmailJob
from accounts.tests.registration_helpers import registration_data


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
@pytest.mark.parametrize("identifier", ["test-member", "member@example.com"])
def test_registration_requires_email_confirmation_before_sign_in(
    client, identifier
):
    """Complete the real email flow before allowing either sign-in mode."""
    credentials = registration_data()
    response = client.post(reverse("register"), credentials)

    assert response.status_code == 302
    assert response.url == reverse("registration_check_email")
    user = User.objects.get(username=credentials["username"])
    assert user.email_verification_required is True
    assert user.is_email_verified is False
    assert not mail.outbox
    assert VerificationEmailJob.objects.get(user=user).status == (
        VerificationEmailJob.Status.PENDING
    )

    login_credentials = {
        "username": identifier,
        "password": credentials["password1"],
    }
    before = client.post(reverse("login"), login_credentials)
    assert before.status_code == 200
    assert "_auth_user_id" not in client.session

    assert deliver_next_verification_email("http://testserver") == (
        DeliveryOutcome.SENT
    )
    assert len(mail.outbox) == 1
    match = re.search(
        r"http://testserver/email/verify/[^/\s]+/[^/\s]+/",
        mail.outbox[0].body,
    )
    assert match is not None
    confirmation_path = urlsplit(match.group()).path

    preview = client.get(confirmation_path)
    assert preview.status_code == 200
    user.refresh_from_db()
    assert user.is_email_verified is False

    confirmed = client.post(confirmation_path)
    assert confirmed.status_code == 302
    assert confirmed.url == reverse("email_verification_result")
    user.refresh_from_db()
    assert user.is_email_verified is True
    assert user.email_verification_required is True

    after = client.post(reverse("login"), login_credentials)
    assert after.status_code == 302
    assert after.url == reverse("home")
    assert client.session["_auth_user_id"] == str(user.pk)
