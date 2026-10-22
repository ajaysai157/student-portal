"""Production settings for the College Management Portal.

Run with::

    DJANGO_SETTINGS_MODULE=college_portal.settings_production python manage.py ...

The differences from the development settings are:

* ``DEBUG`` is always ``False`` - stack traces are never shown to users.
* ``SECRET_KEY`` and ``ALLOWED_HOSTS`` **must** come from the environment.
* Cookies are marked ``Secure`` so they only travel over HTTPS.
* ``SECURE_SSL_REDIRECT`` and HSTS are enabled.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F401,F403  (base configuration)


DEBUG = False

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "django-insecure-development-only-key-change-me-before-deploying":
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a unique value before running in production."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list the deployed host names.")

# Only trust the proxy when the deployment actually sits behind one.
if os.environ.get("DJANGO_BEHIND_HTTPS_PROXY", "false").lower() in {"1", "true", "yes"}:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "true").lower() in {
    "1",
    "true",
    "yes",
}
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_HOST = os.environ.get("DJANGO_SECURE_SSL_HOST") or None

# Show only the "something went wrong" page instead of a stack trace.
INTERNAL_IPS = []
