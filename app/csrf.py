import secrets
from urllib.parse import parse_qs

from markupsafe import Markup
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

CSRF_SESSION_KEY = "_csrf_token"
CSRF_FIELD_NAME = "_csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def get_csrf_token(request: Request) -> str:
    if CSRF_SESSION_KEY not in request.session:
        request.session[CSRF_SESSION_KEY] = secrets.token_hex(32)
    return request.session[CSRF_SESSION_KEY]


def csrf_input(request: Request) -> Markup:
    token = get_csrf_token(request)
    return Markup(f'<input type="hidden" name="{CSRF_FIELD_NAME}" value="{token}">')


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in SAFE_METHODS:
            return await call_next(request)

        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" not in content_type:
            return await call_next(request)

        # Read and cache body so the route handler can still parse it
        body = await request.body()  # caches in request._body

        try:
            form_data = parse_qs(body.decode("utf-8"), keep_blank_values=True)
            token = form_data.get(CSRF_FIELD_NAME, [""])[0]
        except Exception:
            token = ""

        expected = request.session.get(CSRF_SESSION_KEY, "")
        if not expected or not token or not secrets.compare_digest(expected, token):
            return Response("403 Forbidden — CSRF validation failed", status_code=403)

        return await call_next(request)
