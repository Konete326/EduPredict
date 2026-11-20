import time
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from django.views.decorators.debug import sensitive_post_parameters
from accounts.services import (
    SELF_REGISTER_ROLES,
    VALID_ROLES,
    authenticate_user,
    register_user,
    serialize_session_user,
)
from core.db import get_cached, predictions_col
from core.decorators import get_dashboard_route
from core.theme_services import sync_theme_prefs_on_login


def root_redirect(request):
    user = request.session.get("user")
    if isinstance(user, dict):
        role = str(user.get("role") or "").strip().upper()
        if role in VALID_ROLES:
            return redirect(get_dashboard_route(role))
    return redirect("accounts:auth_view")


def _get_live_stats():
    def _fetch():
        try:
            col = predictions_col()
            cnt = int(col.estimated_document_count())
            if cnt <= 0:
                cnt = int(col.count_documents({}))
            return {"predictions_count": max(cnt, 0)}
        except Exception:
            return {"predictions_count": 50}
    return get_cached("auth:live_stats", _fetch, ttl=60.0)


def _render_auth(request, active_tab="login", login_email="", register_data=None):
    stats = _get_live_stats()
    return render(
        request,
        "accounts/auth.html",
        {
            "page_title": "Sign In & Registration",
            "active_tab": active_tab,
            "login_email": login_email,
            "register_data": register_data or {},
            "live_predictions_count": stats.get("predictions_count", 50),
        },
    )


def _handle_login(request):
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    if not email or not password:
        messages.error(request, "Email and password are required.")
        return _render_auth(request, active_tab="login", login_email=email)

    try:
        user_doc, error = authenticate_user(email, password)
    except Exception:
        time.sleep(0.05)
        messages.error(request, "Unable to connect to the database. Please try again.")
        return _render_auth(request, active_tab="login", login_email=email)

    if error or user_doc is None:
        time.sleep(0.05)
        messages.error(request, error or "Invalid email or password.")
        return _render_auth(request, active_tab="login", login_email=email)

    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    sync_theme_prefs_on_login(request, user_doc)
    display_name = session_user["full_name"] or session_user["email"]
    messages.success(request, f"Welcome back, {display_name}!")
    return redirect(get_dashboard_route(session_user["role"]))


def _handle_register(request):
    full_name = (request.POST.get("full_name") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    confirm_password = request.POST.get("confirm_password") or ""
    role = (request.POST.get("role") or "").strip().upper()
    department = (request.POST.get("department") or "").strip()
    batch = (request.POST.get("batch") or "").strip()
    phone = (request.POST.get("phone") or "").strip()
    bio = (request.POST.get("bio") or "").strip()

    register_data = {
        "full_name": full_name,
        "email": email,
        "role": role,
        "department": department,
        "batch": batch,
        "phone": phone,
        "bio": bio,
    }

    if not full_name:
        messages.error(request, "Full name is required.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Please enter a valid email address.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if len(password) < 6:
        messages.error(request, "Password must be at least 6 characters long.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if role not in SELF_REGISTER_ROLES:
        messages.error(request, "Select Student, Teacher, or Data Analyst. Admin accounts are managed internally.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    try:
        user_doc, error = register_user(
            full_name=full_name,
            email=email,
            password=password,
            role=role,
            department=department,
            batch=batch,
            phone=phone,
            bio=bio,
        )
    except Exception:
        messages.error(request, "Unable to complete registration right now. Please try again.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if error or user_doc is None:
        messages.error(request, error or "Registration failed.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if str(user_doc.get("approval_status") or "").strip().upper() == "PENDING":
        messages.warning(
            request,
            "Your teacher account was created and is waiting for Admin approval. You can sign in once an administrator approves it.",
        )
        return _render_auth(request, active_tab="login", login_email=email)

    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    sync_theme_prefs_on_login(request, user_doc)
    display_name = session_user["full_name"] or session_user["email"]
    messages.success(request, f"Account created! Welcome, {display_name}.")
    return redirect(get_dashboard_route(session_user["role"]))


@sensitive_post_parameters("password", "confirm_password")
def auth_view(request):
    user = request.session.get("user")
    if request.method == "GET" and isinstance(user, dict):
        role = str(user.get("role") or "").strip().upper()
        if role in VALID_ROLES:
            return redirect(get_dashboard_route(role))

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "login":
            return _handle_login(request)
        if action == "register":
            return _handle_register(request)
        messages.error(request, "Unsupported authentication request.")
        return _render_auth(request, active_tab="login")

    return _render_auth(request, active_tab="login")


def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been signed out successfully.")
    return redirect("accounts:auth_view")


def error_404(request, exception=None):
    session = getattr(request, "session", None)
    user = session.get("user") if session is not None else None
    active_role = user.get("role") if isinstance(user, dict) else None
    return render(
        request,
        "404.html",
        {
            "page_title": "Page Not Found",
            "active_role": active_role,
        },
        status=404,
    )
