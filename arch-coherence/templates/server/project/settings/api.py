"""API (REST) surface settings. The browsable one: it carries debug_toolbar.

Launched by the api.* vhost (DJANGO_SETTINGS_MODULE=project.settings.api). Only
this surface mounts __debug__/ (in project.urls.apiurls), so debug_toolbar's `djdt`
reverse always resolves here; the mcp surface never loads it.
"""
# Django settings composition idiom: pull the shared base in, override below.
# pylint: disable=wildcard-import,unused-wildcard-import
from .settings import *  # noqa: F401,F403

SURFACE = "api"
ROOT_URLCONF = "project.urls.apiurls"

if DEBUG:  # noqa: F405
    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405
    # debug_toolbar middleware goes right after SecurityMiddleware, before the
    # surface guard.
    MIDDLEWARE = [
        MIDDLEWARE[0],  # noqa: F405
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        *MIDDLEWARE[1:],  # noqa: F405
    ]
