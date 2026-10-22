"""Root URL configuration for the College Management Portal."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django's own admin site - reserved for superusers.
    path("django-admin/", admin.site.urls),
    path("", include("college.urls")),
]

# In development the uploaded media files are served by Django itself.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
