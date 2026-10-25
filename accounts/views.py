"""Views for the Aether accounts application."""

from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView

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
