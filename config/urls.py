"""Root URL configuration for the Aether project."""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("core.urls")),
]
