"""Forms for Aether application authentication."""

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from accounts.models import User


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


# pylint: disable-next=too-many-ancestors
class AetherRegistrationForm(UserCreationForm):
    """Validate credentials for a future public registration page."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        """Reject email addresses already held by another account."""
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                User._meta.get_field("email").error_messages["unique"],
                code="unique",
            )
        return email

    def save(self, commit=True):
        """Always require email verification for public registrations."""
        user = super().save(commit=False)
        user.email_verification_required = True

        if commit:
            user.save()
            self.save_m2m()

        return user
