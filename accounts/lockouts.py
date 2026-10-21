"""Authentication lockout helpers for Aether accounts."""

from django.http import HttpRequest

from accounts.models import User


def get_lockout_username(
    request: HttpRequest,
    credentials: dict | None = None,
) -> str:
    """Resolve username and email aliases to a common lockout identity."""
    if credentials is not None:
        identifier = credentials.get("username")
    else:
        identifier = request.POST.get("username")

    if not isinstance(identifier, str):
        return ""

    if "@" in identifier:
        username = (
            User.objects.filter(email__iexact=identifier)
            .values_list("username", flat=True)
            .first()
        )

        if username is not None:
            return username.casefold()

    return identifier.casefold()
