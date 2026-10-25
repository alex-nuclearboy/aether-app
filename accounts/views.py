"""Views for the Aether accounts application."""

from django.contrib.auth.views import LoginView

from accounts.forms import AetherAuthenticationForm


class AetherLoginView(LoginView):
    """Use Django's standard session login with an Aether-specific form."""

    authentication_form = AetherAuthenticationForm
    template_name = "accounts/login.html"
