"""Views for the Aether accounts application."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView, LogoutView, PasswordChangeView, PasswordResetConfirmView,
)
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from accounts.email_outbox import (
    VerificationQueueStatus,
    queue_verification_email,
)
from accounts.email_verification import verify_email
from accounts.forms import (
    AetherAuthenticationForm,
    AetherEmailCorrectionForm,
    AetherRegistrationForm,
    AetherResendVerificationForm,
    AetherPasswordResetRequestForm,
)
from accounts.models import User
from accounts.password_reset import (
    password_reset_eligible, request_password_reset_email,
)
from accounts.public_recovery import (
    correct_unverified_registration_email,
    request_public_verification_resend,
)
from accounts.public_rate_limits import (
    PublicRequestAction,
    consume_public_request,
    public_request_retry_after,
)
from accounts.registration import create_registration_user
from accounts.tokens import email_verification_token
from infrastructure.request import get_client_ip


class AetherLoginView(LoginView):
    """Use Django's standard session login with an Aether-specific form."""

    authentication_form = AetherAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        """Authenticate the user and confirm a successful sign-in."""
        response = super().form_valid(form)
        messages.success(self.request, _("You have signed in successfully."))
        return response


class AetherLogoutView(LogoutView):
    """End the session and confirm the action on the destination page."""

    def post(self, request, *args, **kwargs):
        """Keep Django's POST-only logout and queue success feedback."""
        response = super().post(request, *args, **kwargs)
        messages.success(request, _("You have signed out successfully."))
        return response


class AetherRegistrationView(TemplateView):
    """Create pending accounts behind a local-only registration gate."""

    template_name = "accounts/register.html"

    def get(self, request, *args, **kwargs):
        """Direct signed-in users to their existing account profile."""
        if request.user.is_authenticated:
            return redirect("profile")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Preserve a bound form and show whether POST is available."""
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = AetherRegistrationForm()
        context["registration_enabled"] = settings.REGISTRATION_ENABLED
        return context

    @staticmethod
    def _registration_limit_response(request):
        """Return a response if the public registration limit blocks a POST."""
        client_ip = get_client_ip(request)
        if client_ip is None:
            response = HttpResponse(
                _("Registration is temporarily unavailable."),
                status=503,
                content_type="text/plain; charset=utf-8",
            )
            response["Cache-Control"] = "no-store"
            return response

        action = PublicRequestAction.REGISTER_IP
        if not consume_public_request(action, client_ip):
            response = HttpResponse(
                _("Too many registration attempts. Please try again later."),
                status=429,
                content_type="text/plain; charset=utf-8",
            )
            response["Retry-After"] = str(public_request_retry_after(action))
            response["Cache-Control"] = "no-store"
            return response

        return None

    def post(self, request, *args, **kwargs):
        """Validate and atomically queue a pending registration account."""
        if request.user.is_authenticated:
            return redirect("profile")

        if not settings.REGISTRATION_ENABLED:
            return HttpResponseNotAllowed(["GET", "HEAD", "OPTIONS"])

        limit_response = self._registration_limit_response(request)
        if limit_response is not None:
            return limit_response

        form = AetherRegistrationForm(request.POST)
        if form.is_valid():
            try:
                create_registration_user(form)
            except ValidationError as error:
                form.add_error(None, error)
            else:
                return redirect("registration_check_email")

        return self.render_to_response(self.get_context_data(form=form))


class RegistrationCheckEmailView(TemplateView):
    """Explain the next step without exposing an email address in a URL."""

    template_name = "accounts/registration_check_email.html"


@method_decorator(never_cache, name="dispatch")
class AetherResendVerificationView(TemplateView):
    """Resend registration links without exposing account membership."""

    template_name = "accounts/registration_resend_email.html"

    def get_context_data(self, **kwargs):
        """Provide a blank or bound form for the public resend page."""
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = AetherResendVerificationForm()
        return context

    @staticmethod
    def _limit_response(request):
        """Enforce the IP allowance before any address lookup."""
        client_ip = get_client_ip(request)
        if client_ip is None:
            response = HttpResponse(
                _("Email recovery is temporarily unavailable."),
                status=503,
                content_type="text/plain; charset=utf-8",
            )
        elif not consume_public_request(
            PublicRequestAction.RESEND_IP, client_ip
        ):
            response = HttpResponse(
                _("Too many requests. Please try again later."),
                status=429,
                content_type="text/plain; charset=utf-8",
            )
            response["Retry-After"] = str(
                public_request_retry_after(PublicRequestAction.RESEND_IP)
            )
        else:
            return None

        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, *args, **kwargs):
        """Queue eligible email while returning a neutral response."""
        limit_response = self._limit_response(request)
        if limit_response is not None:
            return limit_response

        form = AetherResendVerificationForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        email = form.cleaned_data["email"]
        if consume_public_request(PublicRequestAction.RESEND_EMAIL, email):
            request_public_verification_resend(email)
        return redirect("registration_resend_done")


@method_decorator(never_cache, name="dispatch")
class AetherResendDoneView(TemplateView):
    """Show the same result regardless of account existence or state."""

    template_name = "accounts/registration_resend_done.html"


@method_decorator(never_cache, name="dispatch")
@method_decorator(
    sensitive_post_parameters("password"), name="dispatch"
)
class AetherEmailCorrectionView(TemplateView):
    """Correct a never-verified registration address without signing in."""

    template_name = "accounts/registration_correct_email.html"

    def get_context_data(self, **kwargs):
        """Supply a blank or bound non-enumerating correction form."""
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = AetherEmailCorrectionForm()
        return context

    @staticmethod
    def _limit_response(request):
        """Apply the IP allowance before inspecting any credentials."""
        client_ip = get_client_ip(request)
        if client_ip is None:
            response = HttpResponse(
                _("Email correction is temporarily unavailable."),
                status=503,
                content_type="text/plain; charset=utf-8",
            )
        elif not consume_public_request(
            PublicRequestAction.CORRECT_EMAIL_IP, client_ip
        ):
            response = HttpResponse(
                _("Too many requests. Please try again later."),
                status=429,
                content_type="text/plain; charset=utf-8",
            )
            action = PublicRequestAction.CORRECT_EMAIL_IP
            response["Retry-After"] = str(
                public_request_retry_after(action)
            )
        else:
            return None
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, *args, **kwargs):
        """Queue a replacement link and return a neutral result."""
        limit_response = self._limit_response(request)
        if limit_response is not None:
            return limit_response

        form = AetherEmailCorrectionForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        values = form.cleaned_data
        if consume_public_request(
            PublicRequestAction.CORRECT_EMAIL_USERNAME, values["username"]
        ):
            correct_unverified_registration_email(
                values["username"], values["password"],
                values["new_email"],
            )
        return redirect("registration_correct_email_done")


@method_decorator(never_cache, name="dispatch")
class AetherEmailCorrectionDoneView(TemplateView):
    """Show the same response for all valid correction submissions."""

    template_name = "accounts/registration_correct_email_done.html"


@method_decorator(never_cache, name="dispatch")
class AetherPasswordResetRequestView(TemplateView):
    """Accept a neutral password reset request with PostgreSQL limits."""

    template_name = "accounts/password_reset_request.html"

    def get_context_data(self, **kwargs):
        """Provide a blank or bound request form."""
        context = super().get_context_data(**kwargs)
        if "form" not in context:
            context["form"] = AetherPasswordResetRequestForm()
        return context

    def post(self, request, *args, **kwargs):
        """Limit requests, enqueue eligible accounts and redirect neutrally."""
        client_ip = get_client_ip(request)
        if client_ip is None:
            response = HttpResponse(
                _("Password recovery is temporarily unavailable."),
                status=503,
                content_type="text/plain; charset=utf-8",
            )
        elif not consume_public_request(
            PublicRequestAction.RESET_PASSWORD_IP, client_ip
        ):
            response = HttpResponse(
                _("Too many requests. Please try again later."),
                status=429,
                content_type="text/plain; charset=utf-8",
            )
            response["Retry-After"] = str(public_request_retry_after(
                PublicRequestAction.RESET_PASSWORD_IP
            ))
        else:
            response = None
        if response is not None:
            response["Cache-Control"] = "no-store"
            return response

        form = AetherPasswordResetRequestForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))
        email = form.cleaned_data["email"]
        if consume_public_request(
            PublicRequestAction.RESET_PASSWORD_EMAIL, email
        ):
            request_password_reset_email(email)
        return redirect("password_reset_done")


@method_decorator(never_cache, name="dispatch")
class AetherPasswordResetDoneView(TemplateView):
    """Provide the same response for all valid email submissions."""

    template_name = "accounts/password_reset_done.html"


class AetherPasswordResetConfirmView(PasswordResetConfirmView):
    """Use Django's one-time token and password validation flow."""

    template_name = "accounts/password_reset_confirm.html"
    post_reset_login = False

    def get_user(self, uidb64):
        """Disallow recovery after account deactivation or email changes."""
        user = super().get_user(uidb64)
        return user if password_reset_eligible(user) else None

    def dispatch(self, *args, **kwargs):
        """Prevent token-bearing URL paths from reaching referrers."""
        response = super().dispatch(*args, **kwargs)
        response["Referrer-Policy"] = "origin"
        return response


@method_decorator(never_cache, name="dispatch")
class AetherPasswordResetCompleteView(TemplateView):
    """Show password reset completion without authenticating the user."""

    template_name = "accounts/password_reset_complete.html"


@method_decorator(never_cache, name="dispatch")
class AetherPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """Let signed-in users change passwords without ending their session."""

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("profile")

    def form_valid(self, form):
        """Keep Django's password and session handling intact."""
        response = super().form_valid(form)
        messages.success(
            self.request, _("Your password has been changed successfully."),
        )
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    """Present account details without exposing edit controls yet."""

    template_name = "accounts/profile.html"


class RequestEmailVerificationView(LoginRequiredMixin, View):
    """Accept a CSRF-protected request for the signed-in user's email."""

    def post(self, request, *args, **kwargs):
        """Queue a verification link without contacting SMTP in HTTP."""
        status = queue_verification_email(request.user.pk)
        if status == VerificationQueueStatus.QUEUED:
            messages.success(
                request,
                _("A verification email has been queued for delivery."),
            )
        elif status == VerificationQueueStatus.ALREADY_QUEUED:
            messages.info(
                request,
                _("A verification email is already queued for your address."),
            )
        elif status == VerificationQueueStatus.TOO_SOON:
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
