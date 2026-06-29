"""RFC 8414 Authorization Server Metadata. An MCP/OAuth client fetches
/.well-known/oauth-authorization-server to discover the endpoints and the supported PKCE
method (S256 only) before starting the auth-code flow."""
from django.conf import settings
from django.http import JsonResponse


def oauth_authorization_server(request):
    """Serve the RFC 8414 metadata document describing this Authorization Server."""
    issuer = getattr(settings, "AUTH_SERVER_ISSUER", "").rstrip("/")
    scopes = sorted(settings.OAUTH2_PROVIDER.get("SCOPES", {}))
    return JsonResponse(
        {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/o/authorize/",
            "token_endpoint": f"{issuer}/o/token/",
            "introspection_endpoint": f"{issuer}/o/introspect/",
            "revocation_endpoint": f"{issuer}/o/revoke_token/",
            "registration_endpoint": f"{issuer}/o/register/",
            "scopes_supported": scopes,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_basic"],
            "code_challenge_methods_supported": ["S256"],
        }
    )
