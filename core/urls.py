"""
URL configuration for core project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("campaigns.urls")),
    path("accounts/", include("accounts.urls")),
    path("files/", include("datafiles.urls")),
    path("templates/", include("emailtemplates.urls")),
    path("sending-accounts/", include("sending.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
