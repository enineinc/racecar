"""Token-issuance guard: only a WebAuthn session may reach /o/authorize.

A recovery session (backup code or Temporary Access Pass) can enroll a new hardware key but
must never obtain a token — otherwise a recovery secret would be a password-equivalent
bypass of the hardware-key requirement. Fail-closed: no auth_method -> back to login."""
from django.shortcuts import redirect


class TokenIssuanceGuard:
    """Block /o/authorize unless the session came from a hardware-key assertion."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/o/authorize"):
            if request.session.get("auth_method") != "webauthn":
                return redirect(f"/login/?next={request.get_full_path()}")
        return self.get_response(request)
