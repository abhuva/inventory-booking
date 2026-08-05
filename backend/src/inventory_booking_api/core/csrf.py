from secrets import compare_digest

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from inventory_booking_api.settings import get_settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """Require double-submit CSRF tokens for browser session mutations."""

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        has_session = settings.session_cookie_name in request.cookies
        if request.method not in SAFE_METHODS and has_session:
            origin = request.headers.get("origin")
            if origin is not None:
                same_origin = f"{request.url.scheme}://{request.url.netloc}"
                allowed_origins = {*settings.cors_origin_list, same_origin}
                if origin.rstrip("/") not in allowed_origins:
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Invalid request origin."},
                    )

            cookie_token = request.cookies.get(settings.csrf_cookie_name)
            header_token = request.headers.get("X-CSRF-Token")
            if (
                not cookie_token
                or not header_token
                or not compare_digest(cookie_token, header_token)
            ):
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Missing or invalid CSRF token."},
                )

        return await call_next(request)
