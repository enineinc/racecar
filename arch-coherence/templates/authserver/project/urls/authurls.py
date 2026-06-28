"""Authorization Server urlconf (auth process): the OAuth 2.1 endpoints, the
RFC 8414 server metadata, and the WebAuthn login + enrollment ceremonies.

django-oauth-toolkit mounts /o/authorize, /o/token, /o/revoke_token (RFC 7009), and
/o/introspect (RFC 7662). /o/authorize is login-required and LOGIN_URL points at the
WebAuthn login, so a token is only ever issued after a hardware-key assertion. Tokens are
opaque; closed by default (DEFAULT_SCOPES empty, see project.settings.auth)."""
from django.urls import include, path
from oauth_dcr.views import DynamicClientRegistrationView

from apps.authserver import recovery_views, webauthn_views
from apps.authserver.metadata_views import oauth_authorization_server

urlpatterns = [
    path(
        ".well-known/oauth-authorization-server",
        oauth_authorization_server,
        name="oauth-authorization-server",
    ),
    # Dynamic Client Registration (RFC 7591): an MCP client (Claude) registers itself and
    # its redirect URIs, then runs auth-code + PKCE-S256. Open registration, safe defaults.
    path("o/register/", DynamicClientRegistrationView.as_view(), name="oauth2_dcr"),
    path("login/", webauthn_views.login_view, name="login"),
    path("enroll/", webauthn_views.enroll_view, name="enroll"),
    path("webauthn/authenticate/options", webauthn_views.authenticate_options),
    path("webauthn/authenticate/verify", webauthn_views.authenticate_verify),
    path("webauthn/register/options", webauthn_views.register_options),
    path("webauthn/register/verify", webauthn_views.register_verify),
    # Recovery: redeem a backup code or admin TAP for a recovery-only session, then enroll.
    path("recovery/", recovery_views.recovery_page, name="recovery"),
    path("recovery/backup-code", recovery_views.backup_code_redeem),
    path("recovery/tap", recovery_views.tap_redeem),
    path("webauthn/backup-codes", recovery_views.generate_backup_codes),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]
