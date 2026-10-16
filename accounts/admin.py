"""Django admin configuration for Aether accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class AetherUserAdmin(UserAdmin):
    """Admin configuration for Aether user accounts."""

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Personal information",
            {
                "fields": ("email",),
            },
        ),
    )
