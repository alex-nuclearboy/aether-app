"""Forms for Aether application authentication."""

from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class AetherAuthenticationForm(AuthenticationForm):
    """Present username-or-email login without exposing account details."""

    error_messages = {
        "invalid_login": _(
            "Please enter a valid username or email and password."
        ),
        "inactive": _(
            "Please enter a valid username or email and password."
        ),
    }

    def __init__(self, *args, **kwargs):
        """Label Django's standard identifier field for both login modes."""
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Username or email")
