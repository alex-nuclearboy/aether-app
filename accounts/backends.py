
"""Username-or-email authentication for Aether accounts."""

from asgiref.sync import sync_to_async
from axes.backends import AxesStandaloneBackend
from django.contrib.auth import (
    acheck_password_with_timing_attack_mitigation,
    check_password_with_timing_attack_mitigation,
)
from django.contrib.auth.backends import ModelBackend
from django.views.decorators.debug import sensitive_variables

from accounts.models import User


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate users by username or email, ignoring case."""

    @staticmethod
    def _identifier_lookup(identifier: str) -> dict[str, str]:
        """Select the lookup based on the identifier format."""
        if "@" in identifier:
            return {"email__iexact": identifier}

        return {"username__iexact": identifier}

    @sensitive_variables("password")
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate using Django's password verification."""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            user = User.objects.get(
                **self._identifier_lookup(username)
            )
        except User.DoesNotExist:
            user = None

        if (
            check_password_with_timing_attack_mitigation(user, password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None

    @sensitive_variables("password")
    async def aauthenticate(
        self, request, username=None, password=None, **kwargs
    ):
        """Authenticate asynchronously using the same identifier rules."""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            user = await User.objects.aget(
                **self._identifier_lookup(username)
            )
        except User.DoesNotExist:
            user = None

        if (
            await acheck_password_with_timing_attack_mitigation(
                user, password
            )
            and self.user_can_authenticate(user)
        ):
            return user

        return None


class AsyncAxesStandaloneBackend(AxesStandaloneBackend):
    """Enforce Axes lockouts during synchronous and asynchronous login."""

    @sensitive_variables("password")
    async def aauthenticate(
        self, request, username=None, password=None, **kwargs
    ):
        """Run Axes lockout checks safely from asynchronous authentication."""
        return await sync_to_async(
            self.authenticate,
            thread_sensitive=True,
        )(
            request,
            username=username,
            password=password,
            **kwargs,
        )
