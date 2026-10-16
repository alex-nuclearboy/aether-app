"""User models for the Aether accounts application."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Aether user account."""

    email = models.EmailField(
        "email address",
        unique=True,
    )
