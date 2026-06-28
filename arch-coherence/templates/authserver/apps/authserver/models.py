"""The Authorization Server's state — this app is the only DB owner.

django-oauth-toolkit owns the token/application/grant tables; this module owns the
WebAuthn credential store (enrolled hardware keys) and the recovery material (backup codes,
Temporary Access Passes). Stage 6 adds AuditLog."""
import logging

from django.conf import settings
from django.db import models
from django.utils import timezone

_log = logging.getLogger("racecar.authserver.audit")


class WebAuthnCredential(models.Model):
    """An enrolled FIDO2 hardware key — one row per authenticator per user.

    Written by the registration ceremony and read by the authentication ceremony. A user
    may enroll several keys (recovery). credential_id is the base64url id the browser
    reports, so login can look the key up without decoding."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="webauthn_credentials",
    )
    credential_id = models.CharField(max_length=512, unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    aaguid = models.CharField(max_length=36, blank=True, default="")
    transports = models.JSONField(default=list, blank=True)
    nickname = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user}: {self.nickname or self.aaguid or 'key'}"


class BackupCode(models.Model):
    """A one-time recovery code, stored hashed. Redeeming it grants a recovery-only session
    that can enroll a new hardware key but never obtain a token."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="backup_codes"
    )
    code_hash = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)


class TemporaryAccessPass(models.Model):
    """An admin-issued, time-limited, single-use pass (the issue_tap management command).
    Redeeming it grants a recovery-only session to enroll a new key — the way back in after
    every hardware key is lost."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="access_passes"
    )
    code_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_valid(self):
        """True while the pass is unused and unexpired."""
        return self.used_at is None and self.expires_at > timezone.now()


class AuditLog(models.Model):
    """The AS access trail: one row per auth event (login, recovery, enrollment).

    Per-tool-call access is logged at the surfaces (database-light); this is the AS side —
    who authenticated, how, and from where. user is nullable: a failed login has no user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    event = models.CharField(max_length=64)
    detail = models.CharField(max_length=255, blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


def _client_ip(request):
    """Best-effort client IP for the audit log. Trusts the first X-Forwarded-For hop,
    which is meaningful ONLY behind a trusted proxy that sets it (the Apache vhost); a
    direct or untrusted deployment must treat this as advisory, since XFF is spoofable."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")


def record_event(request, event, *, user=None, detail=""):
    """Write an AuditLog row from a request (best-effort, never raises into the flow)."""
    try:
        AuditLog.objects.create(
            user=user, event=event, detail=detail[:255], ip=_client_ip(request)
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # A lost audit row is itself a security signal -- log it rather than vanish.
        _log.warning("audit write failed (event=%s): %s", event, exc)
