"""Per-surface host guard: a host middleware that never swaps the urlconf.

Each process serves exactly one surface: its DJANGO_SETTINGS_MODULE
(project.settings.api | project.settings.mcp) fixes ROOT_URLCONF at boot. This
middleware attaches `request.surface` and 404s a request whose host clearly belongs
to the other surface. It never assigns `request.urlconf` -- surface selection is
boot-time, per process, not per request.
"""
from django.conf import settings
from django.http import HttpResponseNotFound


class SurfaceHostMiddleware:
    """Attach request.surface from settings.SURFACE; 404 a host bound to the other surface."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.surface = getattr(settings, "SURFACE", "api")
        host = request.get_host().split(":")[0]
        other_prefix = "mcp." if request.surface == "api" else "api."
        if host.startswith(other_prefix):
            return HttpResponseNotFound(b"host does not match this surface")
        return self.get_response(request)
