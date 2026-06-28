"""WSGI entry (present for parity; the surfaces run under ASGI)."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.api")
application = get_wsgi_application()
