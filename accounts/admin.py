"""Django admin configuration for Aether accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from accounts.models import User


@admin.register(User)
class AetherUserAdmin(UserAdmin):
    """Admin configuration for Aether user accounts."""

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            _("Personal info"),
            {
                "fields": ("email",),
            },
        ),
    )
