"""Project-level views (api surface): serve the generated OpenAPI document."""
import json

from django.conf import settings
from django.http import JsonResponse

_OPENAPI_PATH = settings.BASE_DIR / "docs" / "api" / "openapi.json"
try:
    _OPENAPI = json.loads(_OPENAPI_PATH.read_text())
except (OSError, ValueError):  # missing file or malformed JSON -> serve empty
    _OPENAPI = {}


def openapi(request):
    """Serve the generated OpenAPI 3.1 document (docs/api/openapi.json)."""
    return JsonResponse(_OPENAPI)
