"""WebAuthn ceremonies (py_webauthn >= 2.0) gating the Authorization Server.

A token is only ever issued after a hardware-key assertion: DOT's /o/authorize is
login-required (LOGIN_URL = /login/), and the ONLY way to an authenticated session is the
authentication ceremony here. There is no password backend exposed.

Hardware-key-only is enforced at enrollment: cross-platform attachment, user verification
required, direct attestation, and an AAGUID whitelist (settings.WEBAUTHN_ALLOWED_AAGUIDS,
fail-closed when empty) so synced/platform passkeys are rejected. Login is usernameless:
the authenticator is a discoverable (resident) credential, so the assertion identifies the
user by the stored credential id.

This ceremony is verified against a real authenticator at Stage 7."""
import json
import logging

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

import webauthn
from webauthn import base64url_to_bytes, options_to_json
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AttestationFormat,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..models import WebAuthnCredential, record_event

_AUTH_CHALLENGE = "webauthn_auth_challenge"
_REG_CHALLENGE = "webauthn_reg_challenge"
_BACKEND = "django.contrib.auth.backends.ModelBackend"
_log = logging.getLogger("racecar.authserver.webauthn")


def _json_options(request, options, key):
    """Stash the challenge in the session and return the options as WebAuthn JSON."""
    request.session[key] = webauthn.helpers.bytes_to_base64url(options.challenge)
    return JsonResponse(json.loads(options_to_json(options)))


def _pop_challenge(request, key):
    """Recover the raw challenge bytes the ceremony was issued with."""
    stashed = request.session.pop(key, None)
    return base64url_to_bytes(stashed) if stashed else None


@ensure_csrf_cookie
def login_view(request):
    """Serve the WebAuthn login page — the only way to an authenticated session."""
    return render(
        request,
        "authserver/login.html",
        {"next": request.GET.get("next", "/o/authorize/")},
    )


@require_POST
def authenticate_options(request):
    """Begin login: issue a challenge for a discoverable (usernameless) assertion."""
    options = webauthn.generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return _json_options(request, options, _AUTH_CHALLENGE)


@require_POST
def authenticate_verify(request):
    """Complete login: verify the assertion, then attach the session (the one gate)."""
    challenge = _pop_challenge(request, _AUTH_CHALLENGE)
    if challenge is None:
        return HttpResponseForbidden("no challenge in session")
    raw = request.body.decode()
    body = json.loads(raw)
    cred = WebAuthnCredential.objects.filter(credential_id=body.get("id")).first()
    if cred is None:
        record_event(request, "login.failure", detail="unknown credential")
        # Opaque to the client (no credential-existence oracle); the specific reason is audited.
        return HttpResponseForbidden("authentication failed")
    try:
        verification = webauthn.verify_authentication_response(
            credential=raw,
            expected_challenge=challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=bytes(cred.public_key),
            credential_current_sign_count=cred.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Detail is audited; do not echo the raw ceremony internals to the client.
        record_event(request, "login.failure", user=cred.user, detail=str(exc)[:120])
        return HttpResponseForbidden("authentication failed")
    cred.sign_count = verification.new_sign_count
    cred.last_used_at = timezone.now()
    cred.save(update_fields=["sign_count", "last_used_at"])
    login(request, cred.user, backend=_BACKEND)
    # Mark the session as hardware-key authenticated: only this may issue tokens. A
    # recovery session (backup code / TAP) is "recovery" and TokenIssuanceGuard blocks it.
    request.session["auth_method"] = "webauthn"
    record_event(request, "login.success", user=cred.user)
    return JsonResponse({"verified": True, "next": request.GET.get("next", "/o/authorize/")})


@ensure_csrf_cookie
@login_required
def enroll_view(request):
    """Serve the enrollment page — drives the registration ceremony to add a hardware key.

    Reachable by a hardware-key session (add a spare key) or a recovery session (the way
    back in after a loss); either way it can only add a key, never issue a token."""
    return render(request, "authserver/enroll.html", {})


@login_required
@require_POST
def register_options(request):
    """Begin enrollment (for an already-authenticated user): force a hardware key."""
    existing = WebAuthnCredential.objects.filter(user=request.user)
    options = webauthn.generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_name=request.user.get_username(),
        user_id=str(request.user.pk).encode(),
        attestation=AttestationConveyancePreference.DIRECT,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id))
            for c in existing
        ],
    )
    return _json_options(request, options, _REG_CHALLENGE)


@login_required
@require_POST
def register_verify(request):
    """Complete enrollment: verify attestation, enforce the AAGUID whitelist, store key."""
    challenge = _pop_challenge(request, _REG_CHALLENGE)
    if challenge is None:
        return HttpResponseForbidden("no challenge in session")
    raw = request.body.decode()
    body = json.loads(raw)
    # When attestation roots are configured the chain is verified, so verification.aaguid is
    # trustworthy; unconfigured, the AAGUID is self-reported and the whitelist is advisory.
    roots = settings.WEBAUTHN_PACKED_ROOT_CERTS
    if not roots:
        _log.warning(
            "enrolling without attestation roots: AAGUID is self-reported (advisory); "
            "set WEBAUTHN_PACKED_ROOT_CERTS for true hardware binding"
        )
    try:
        verification = webauthn.verify_registration_response(
            credential=raw,
            expected_challenge=challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=True,
            pem_root_certs_bytes_by_fmt={AttestationFormat.PACKED: roots} if roots else None,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _log.warning("registration attestation failed: %s", exc)
        return HttpResponseForbidden("attestation failed")
    # Hardware-key whitelist, fail-closed: an empty whitelist enrolls nothing.
    allowed = settings.WEBAUTHN_ALLOWED_AAGUIDS
    if not allowed:
        return HttpResponseForbidden("enrollment closed: WEBAUTHN_ALLOWED_AAGUIDS unset")
    if verification.aaguid not in allowed:
        return HttpResponseForbidden(f"authenticator {verification.aaguid} not whitelisted")
    WebAuthnCredential.objects.create(
        user=request.user,
        credential_id=body.get("id"),
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        aaguid=verification.aaguid,
        transports=body.get("response", {}).get("transports", []),
        nickname=request.GET.get("nickname", ""),
    )
    record_event(request, "enroll", user=request.user, detail=verification.aaguid)
    return JsonResponse({"verified": True})
