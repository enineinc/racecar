"""ASGI entry: `uvicorn project.asgi:application`. Each process picks its surface
via DJANGO_SETTINGS_MODULE (project.settings.api | project.settings.mcp); the
default here is only a fallback for a bare launch."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.api")
application = get_asgi_application()
