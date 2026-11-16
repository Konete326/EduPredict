from functools import wraps
from django.contrib import messages
from django.contrib.messages.api import MessageFailure
from django.shortcuts import redirect

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
