import time
from functools import wraps
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect

_RATE_LIMIT_BUCKETS = {}


def _clear_rate_limit_buckets():
    _RATE_LIMIT_BUCKETS.clear()


def rate_limit(max_requests=60, window_seconds=60):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
            client_ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "unknown")
            view_name = view_func.__name__
            key = f"{view_name}:{client_ip}"
            now = time.monotonic()

            bucket = _RATE_LIMIT_BUCKETS.get(key)
            if bucket is None:
                bucket = []
                _RATE_LIMIT_BUCKETS[key] = bucket

            cutoff = now - window_seconds
            _RATE_LIMIT_BUCKETS[key] = [t for t in bucket if t > cutoff]

            if len(_RATE_LIMIT_BUCKETS[key]) >= max_requests:
                oldest_timestamp = _RATE_LIMIT_BUCKETS[key][0]
                wait_seconds = max(1, int(window_seconds - (now - oldest_timestamp)) + 1)
                accept_header = request.headers.get("accept", "")
                if accept_header.startswith("application/json") or request.path.startswith("/health/"):
                    response = JsonResponse(
                        {
                            "error": "Too many requests. Please slow down and try again.",
                            "retry_after_seconds": wait_seconds,
                        },
                        status=429,
                    )
                    response["Retry-After"] = str(wait_seconds)
                    return response
                _queue_message(
                    messages.error,
                    request,
                    "Too many requests. Please slow down and try again.",
                )
                response = HttpResponse("Too Many Requests", status=429)
                response["Retry-After"] = str(wait_seconds)
                return response

            _RATE_LIMIT_BUCKETS[key].append(now)

            if len(_RATE_LIMIT_BUCKETS) > 1000:
                stale_keys = [k for k, timestamps in _RATE_LIMIT_BUCKETS.items() if not timestamps or timestamps[-1] <= cutoff]
                for k in stale_keys:
                    _RATE_LIMIT_BUCKETS.pop(k, None)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator

ROLE_DASHBOARD_MAP = {
    "ADMIN": "panels:admin_dashboard",
    "TEACHER": "panels:teacher_dashboard",
    "STUDENT": "panels:student_dashboard",
    "ANALYST": "panels:analyst_dashboard",
}


def _queue_message(level_fn, request, text):
    try:
        level_fn(request, text)
    except MessageFailure:
        pass


def get_dashboard_route(role):
    normalized_role = str(role or "").strip().upper()
    return ROLE_DASHBOARD_MAP.get(normalized_role, "accounts:auth_view")


def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        session = getattr(request, "session", None)
        user = session.get("user") if session is not None else None
        if not isinstance(user, dict) or not user:
            _queue_message(
                messages.warning,
                request,
                "Please sign in to access this page.",
            )
            return redirect("accounts:auth_view")
        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(allowed_roles):
    if isinstance(allowed_roles, str):
        normalized_roles = {allowed_roles.strip().upper()}
    else:
        normalized_roles = {str(role).strip().upper() for role in allowed_roles}

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            session = getattr(request, "session", None)
            user = session.get("user") if session is not None else None
            if not isinstance(user, dict) or not user:
                _queue_message(
                    messages.warning,
                    request,
                    "Please sign in to access this page.",
                )
                return redirect("accounts:auth_view")

            user_role = str(user.get("role") or "").strip().upper()
            if user_role not in normalized_roles:
                _queue_message(
                    messages.error,
                    request,
                    "Access denied. Redirected to your dashboard.",
                )
                return redirect(get_dashboard_route(user_role))

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
