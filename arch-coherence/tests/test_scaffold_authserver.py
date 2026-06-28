"""scaffold_authserver: the auth.* Authorization Server is generated closed by default.

The generator emits pure text (no Django import), so these assertions check the
load-bearing facts in the emitted files without django-oauth-toolkit installed."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "arch-coherence" / "scripts"))
import scaffold_authserver  # noqa: E402


def _shell(root: Path) -> Path:
    """A minimal server shell tree the additive generator writes into."""
    (root / "project" / "settings").mkdir(parents=True)
    (root / "project" / "urls").mkdir(parents=True)
    (root / "apps").mkdir(parents=True)
    return root


def test_emits_the_auth_process_files(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    for rel in (
        "project/settings/auth.py",
        "project/urls/authurls.py",
        "apps/authserver/metadata_views.py",
        "apps/authserver/apps.py",
        "apps/authserver/migrations/__init__.py",
        "apache/auth.vhost.conf",
        "run-auth.sh",
    ):
        assert (tmp_path / rel).exists(), rel


def test_closed_by_default(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    # The cardinal override: DOT defaults DEFAULT_SCOPES to ["__all__"] (wide-open);
    # the generator forces it empty so a token carries no scope unless granted.
    assert '"DEFAULT_SCOPES": []' in settings
    assert '"PKCE_REQUIRED": True' in settings
    assert 'SURFACE = "auth"' in settings


def test_opaque_tokens_never_jwt(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    # The comments document "never JWT" as doctrine; assert no JWT is *configured*
    # (no token generator, no jwt contrib) by checking the code lines, not the prose.
    code = "\n".join(
        line for line in settings.splitlines() if not line.lstrip().startswith("#")
    )
    assert "jwt" not in code.lower()


def test_as_apps_and_endpoints_mounted(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    assert "oauth2_provider" in settings and '"apps.authserver"' in settings
    urls = (tmp_path / "project" / "urls" / "authurls.py").read_text()
    assert "oauth2_provider.urls" in urls
    assert "oauth-authorization-server" in urls


def test_metadata_advertises_s256_and_the_endpoints(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    meta = (tmp_path / "apps" / "authserver" / "metadata_views.py").read_text()
    assert "S256" in meta
    for endpoint in ("authorize", "token", "introspect", "revoke_token"):
        assert endpoint in meta, endpoint


def test_issuer_is_threaded(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path), issuer="https://auth.gfem.test")
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    assert "https://auth.gfem.test" in settings


# --- Unit B: WebAuthn hardware-key login -----------------------------------------


def test_credential_model_shape(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    models = (tmp_path / "apps" / "authserver" / "models.py").read_text()
    assert "class WebAuthnCredential" in models
    assert "credential_id = models.CharField(max_length=512, unique=True)" in models
    assert "public_key = models.BinaryField()" in models
    assert "sign_count" in models and "aaguid" in models
    assert "settings.AUTH_USER_MODEL" in models  # no coupling to the business package


def test_hardware_key_only_enforced(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    views = (tmp_path / "apps" / "authserver" / "webauthn_views.py").read_text()
    # Cross-platform (no synced/platform passkeys) + user verification + direct attestation.
    assert "AuthenticatorAttachment.CROSS_PLATFORM" in views
    assert "UserVerificationRequirement.REQUIRED" in views
    assert "AttestationConveyancePreference.DIRECT" in views
    # AAGUID whitelist, fail-closed when empty.
    assert "WEBAUTHN_ALLOWED_AAGUIDS" in views
    assert "enrollment closed" in views


def test_all_four_ceremonies_present(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    views = (tmp_path / "apps" / "authserver" / "webauthn_views.py").read_text()
    for fn in (
        "generate_registration_options",
        "verify_registration_response",
        "generate_authentication_options",
        "verify_authentication_response",
    ):
        assert fn in views, fn


def test_no_password_login_path(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    views = (tmp_path / "apps" / "authserver" / "webauthn_views.py").read_text()
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    # The only login is the WebAuthn ceremony: LOGIN_URL points at it, and no password
    # primitive is used (login() attaches the session after the assertion verifies). The
    # docstrings mention "password" to document its absence, so check for the primitives.
    assert 'LOGIN_URL = "/login/"' in settings
    assert "check_password" not in views
    assert "AuthenticationForm" not in views
    assert "django.contrib.admin" not in settings  # no admin password backdoor


def test_login_template_and_deps(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    page = (tmp_path / "apps" / "authserver" / "templates" / "authserver" / "login.html")
    assert page.exists()
    assert "navigator.credentials.get" in page.read_text()
    assert "webauthn>=2.0" in scaffold_authserver.AUTH_RUNTIME_DEPS


# --- Unit C: recovery (backup codes, admin TAP, recovery-only sessions) ----------


def test_recovery_models(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    models = (tmp_path / "apps" / "authserver" / "models.py").read_text()
    assert "class BackupCode" in models
    assert "class TemporaryAccessPass" in models
    assert "code_hash" in models  # secrets stored hashed, never in the clear
    assert "expires_at" in models  # the TAP is time-limited


def test_recovery_session_cannot_issue_tokens(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    guard = (tmp_path / "apps" / "authserver" / "middleware.py").read_text()
    recovery = (tmp_path / "apps" / "authserver" / "recovery_views.py").read_text()
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    # The guard blocks /o/authorize unless the session is hardware-key authenticated.
    assert "/o/authorize" in guard and 'auth_method") != "webauthn"' in guard
    assert "apps.authserver.middleware.TokenIssuanceGuard" in settings
    # Recovery redemption attaches a recovery (not webauthn) session.
    assert 'session["auth_method"] = "recovery"' in recovery


def test_recovery_secrets_are_hashed(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    recovery = (tmp_path / "apps" / "authserver" / "recovery_views.py").read_text()
    # Stored via make_password, verified via check_password — never compared in the clear.
    assert "make_password" in recovery and "check_password" in recovery


def test_admin_tap_is_a_management_command(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    cmd = (
        tmp_path / "apps" / "authserver" / "management" / "commands" / "issue_tap.py"
    )
    assert cmd.exists()  # no web admin login: the admin path is a server-run command
    assert "class Command(BaseCommand)" in cmd.read_text()


def test_csrf_protection_present(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    assert "django.middleware.csrf.CsrfViewMiddleware" in settings
    login = (tmp_path / "apps" / "authserver" / "templates" / "authserver" / "login.html")
    assert "X-CSRFToken" in login.read_text()


# --- Unit D: dynamic client registration (RFC 7591) ------------------------------


def test_dcr_registration_endpoint(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    settings = (tmp_path / "project" / "settings" / "auth.py").read_text()
    urls = (tmp_path / "project" / "urls" / "authurls.py").read_text()
    meta = (tmp_path / "apps" / "authserver" / "metadata_views.py").read_text()
    assert '"oauth_dcr"' in settings
    assert "DynamicClientRegistrationView" in urls and "o/register/" in urls
    assert "registration_endpoint" in meta  # advertised in RFC 8414 metadata
    assert "django-oauth-toolkit-dcr" in scaffold_authserver.AUTH_RUNTIME_DEPS


# --- Stage 6: audit (AS-side auth-event trail) -----------------------------------


def test_audit_log_model_and_helper(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    models = (tmp_path / "apps" / "authserver" / "models.py").read_text()
    assert "class AuditLog" in models
    assert "event = models.CharField" in models and "ip = models.GenericIPAddressField" in models
    assert "def record_event(" in models


def test_auth_events_are_recorded(tmp_path):
    scaffold_authserver.render_authserver(_shell(tmp_path))
    webauthn = (tmp_path / "apps" / "authserver" / "webauthn_views.py").read_text()
    recovery = (tmp_path / "apps" / "authserver" / "recovery_views.py").read_text()
    assert '"login.success"' in webauthn and '"login.failure"' in webauthn
    assert '"enroll"' in webauthn
    assert '"recovery.backup"' in recovery and '"recovery.tap"' in recovery
