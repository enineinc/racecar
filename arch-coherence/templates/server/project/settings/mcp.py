"""MCP surface settings. The machine one: no debug_toolbar, no extras.

Launched by the mcp.* vhost (DJANGO_SETTINGS_MODULE=project.settings.mcp).
"""
# Django settings composition idiom: pull the shared base in, override below.
# pylint: disable=wildcard-import,unused-wildcard-import
from .settings import *  # noqa: F401,F403

SURFACE = "mcp"
ROOT_URLCONF = "project.urls.mcpurls"
