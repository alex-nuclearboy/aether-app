"""Views for the Aether accounts application."""

from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from accounts.email_verification import verify_email
from accounts.emails import (
    VerificationEmailStatus,
    send_verification_email,
)
from accounts.models import User
from accounts.tokens import email_verification_token

from accounts.forms import AetherAuthenticationForm


class AetherLoginView(LoginView):
    """Use Django's standard session login with an Aether-specific form."""

    authentication_form = AetherAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        """Authenticate the user and confirm a successful sign-in."""
        response = super().form_valid(form)
        messages.success(self.request, "You have signed in successfully.")
        return response


class AetherLogoutView(LogoutView):
    """End the session and confirm the action on the destination page."""

    def post(self, request, *args, **kwargs):
        """Keep Django's POST-only logout and queue success feedback."""
        response = super().post(request, *args, **kwargs)
        messages.success(request, "You have signed out successfully.")
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """Present account details without exposing edit controls yet."""

    template_name = "accounts/profile.html"


class RequestEmailVerificationView(LoginRequiredMixin, View):
    """Accept a CSRF-protected request for the signed-in user's email."""

    def post(self, request, *args, **kwargs):
        """Send a verification link unless already verified or throttled."""
        try:
            status = send_verification_email(request, request.user.pk)
        except (OSError, SMTPException):
            messages.error(
                request,
                _("We couldn't send the email. Please try again later."),
            )
        else:
            if status == VerificationEmailStatus.SENT:
                messages.success(
                    request,
                    _("A verification link has been sent to your email."),
                )
            elif status == VerificationEmailStatus.TOO_SOON:
                messages.warning(
                    request,
                    _("Please wait before requesting another email."),
                )
            else:
                messages.info(request, _("Your email is already verified."))

        return redirect("profile")


@method_decorator(never_cache, name="dispatch")
class EmailVerificationConfirmView(View):
    """Display confirmation on GET and apply verification only on POST."""

    def dispatch(self, request, *args, **kwargs):
        """Prevent verification tokens from leaking through referrers."""
        response = super().dispatch(request, *args, **kwargs)
        response["Referrer-Policy"] = "origin"
        return response

    @staticmethod
    def _user(uidb64):
        """Resolve a user identifier without disclosing lookup errors."""
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.filter(pk=user_id).first()
        except (TypeError, ValueError, OverflowError, ValidationError):
            return None

    def get(self, request, uidb64, token):
        """Offer a deliberate confirmation action without mutating data."""
        user = self._user(uidb64)
        valid = bool(
            user
            and not user.is_email_verified
            and email_verification_token.check_token(user, token)
        )
        return render(
            request,
            "accounts/email_verification_confirm.html",
            {"valid_token": valid, "uidb64": uidb64, "token": token},
        )

    def post(self, request, uidb64, token):
        """Consume a valid token, then redirect to a token-free page."""
        user = self._user(uidb64)
        if user is not None and verify_email(user.pk, token):
            messages.success(request, _("Your email has been verified."))
        else:
            messages.error(
                request,
                _("This verification link is invalid or has expired."),
            )
        return redirect("email_verification_result")


class EmailVerificationResultView(TemplateView):
    """Provide a token-free destination after a confirmation POST."""

    template_name = "accounts/email_verification_result.html"
