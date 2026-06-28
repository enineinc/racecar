"""Recovery: backup codes and admin Temporary Access Passes.

Both grant a RECOVERY-ONLY session (auth_method="recovery") that can enroll a new hardware
key but never obtain a token (TokenIssuanceGuard enforces that) — the way back in after a
key is lost. Codes and passes are stored hashed; redemption is single-use."""
import json
import secrets

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import BackupCode, TemporaryAccessPass, record_event

_BACKEND = "django.contrib.auth.backends.ModelBackend"
# Recovery secrets are password-equivalent; the redeem endpoints are unauthenticated, so
# throttle online guessing: N failures per (username, IP) arms a cooldown window.
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900


def _throttle_key(request, username):
    """Attempt-counter cache key, scoped to (username, client IP)."""
    return f"recovery_attempts:{username}:{request.META.get('REMOTE_ADDR', '')}"


def _too_many_attempts(request, username):
    """True once this (username, IP) has burned its recovery attempt budget.

    Backed by the Django cache. The AS runs as a single process, so the default
    LocMemCache suffices; a multi-worker deploy must configure a shared cache."""
    return cache.get(_throttle_key(request, username), 0) >= _MAX_ATTEMPTS


def _record_failed_attempt(request, username):
    """Count one failed redemption against the lockout window."""
    key = _throttle_key(request, username)
    cache.add(key, 0, _LOCKOUT_SECONDS)  # arm the window on the first failure only
    try:
        cache.incr(key)
    except ValueError:  # the window expired between add and incr
        cache.set(key, 1, _LOCKOUT_SECONDS)


@login_required
@require_POST
def generate_backup_codes(request):
    """Issue a fresh set of one-time backup codes, invalidating any unused old ones."""
    BackupCode.objects.filter(user=request.user, used_at__isnull=True).delete()
    codes = [secrets.token_hex(5) for _ in range(10)]
    BackupCode.objects.bulk_create(
        [BackupCode(user=request.user, code_hash=make_password(c)) for c in codes]
    )
    return JsonResponse({"codes": codes})  # shown once, never stored in the clear


@ensure_csrf_cookie
def recovery_page(request):
    """The recovery page: redeem a backup code or a TAP, then enroll a new key."""
    return render(request, "authserver/recovery.html", {})


def _start_recovery(request, user):
    """Attach a recovery-only session — enrollment yes, token issuance no."""
    login(request, user, backend=_BACKEND)
    request.session["auth_method"] = "recovery"


@require_POST
def backup_code_redeem(request):
    """Redeem a one-time backup code for a recovery session."""
    body = json.loads(request.body.decode())
    username, code = body.get("username", ""), body.get("code", "")
    if _too_many_attempts(request, username):
        return HttpResponse("too many attempts; retry after the cooldown", status=429)
    for entry in BackupCode.objects.filter(user__username=username, used_at__isnull=True):
        if check_password(code, entry.code_hash):
            entry.used_at = timezone.now()
            entry.save(update_fields=["used_at"])
            cache.delete(_throttle_key(request, username))  # reset the throttle on success
            _start_recovery(request, entry.user)
            record_event(request, "recovery.backup", user=entry.user)
            return JsonResponse({"verified": True, "next": "/enroll/"})
    _record_failed_attempt(request, username)
    record_event(request, "recovery.backup.failure", detail=username)
    return HttpResponseForbidden("invalid or used code")


@require_POST
def tap_redeem(request):
    """Redeem an admin Temporary Access Pass for a recovery session."""
    body = json.loads(request.body.decode())
    username, code = body.get("username", ""), body.get("code", "")
    if _too_many_attempts(request, username):
        return HttpResponse("too many attempts; retry after the cooldown", status=429)
    passes = TemporaryAccessPass.objects.filter(user__username=username, used_at__isnull=True)
    for entry in passes:
        if entry.is_valid() and check_password(code, entry.code_hash):
            entry.used_at = timezone.now()
            entry.save(update_fields=["used_at"])
            cache.delete(_throttle_key(request, username))  # reset the throttle on success
            _start_recovery(request, entry.user)
            record_event(request, "recovery.tap", user=entry.user)
            return JsonResponse({"verified": True, "next": "/enroll/"})
    _record_failed_attempt(request, username)
    record_event(request, "recovery.tap.failure", detail=username)
    return HttpResponseForbidden("invalid, used, or expired pass")
