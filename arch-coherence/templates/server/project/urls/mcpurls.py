"""MCP surface urlconf (mcp process): the single Streamable-HTTP endpoint."""
from django.urls import path

from apps import mcp

urlpatterns = [
    path("mcp", mcp.endpoint, name="mcp"),
    path("mcp/", mcp.endpoint),
    # RFC 9728: an MCP client fetches this to discover the Authorization Server.
    path(
        ".well-known/oauth-protected-resource",
        mcp.protected_resource_metadata,
        name="oauth-protected-resource",
    ),
]
