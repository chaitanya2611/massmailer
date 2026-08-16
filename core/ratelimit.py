"""
Lightweight IP-based rate limiting for anti-abuse on public endpoints
(signup, login) using Django's cache framework — no external service or
API key needed. Render's free plan runs a single web dyno, so the default
LocMemCache is enough for this; counts reset on restart/deploy, which is
an acceptable trade-off for a v1 abuse deterrent rather than a hard
security boundary. Swap in a shared cache backend (e.g. Redis) first if
you move to multiple dynos.
"""
from functools import wraps

from django.http import HttpResponse


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def rate_limit(action: str, limit: int, window_seconds: int):
    """Allow at most `limit` POSTs to the wrapped view per client IP per
    `window_seconds`. Non-POST requests (e.g. the initial GET of a form)
    always pass through untouched."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.method == "POST":
                from django.core.cache import cache  # imported lazily so settings are ready

                key = f"ratelimit:{action}:{_client_ip(request)}"
                count = cache.get(key, 0)
                if count >= limit:
                    return HttpResponse(
                        "Too many attempts from this network. Please wait a while before trying again.",
                        status=429,
                    )
                cache.set(key, count + 1, timeout=window_seconds)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
