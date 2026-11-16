from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render
from accounts.services import (
    VALID_ROLES,
    authenticate_user,
    register_user,
    serialize_session_user,
)
from core.decorators import get_dashboard_route


def root_redirect(request):
    user = request.session.get("user")
    if isinstance(user, dict):
        role = str(user.get("role") or "").strip().upper()
        if role in VALID_ROLES:
            return redirect(get_dashboard_route(role))
    return redirect("accounts:auth_view")


def _render_auth(request, active_tab="login", login_email="", register_data=None):
    return render(
        request,
        "accounts/auth.html",
        {
            "page_title": "Sign In & Registration",
            "active_tab": active_tab,
            "login_email": login_email,
            "register_data": register_data or {},
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
        messages.error(request, "Unable to connect to the database. Please try again.")
        return _render_auth(request, active_tab="login", login_email=email)

    if error or user_doc is None:
        messages.error(request, error or "Invalid email or password.")
        return _render_auth(request, active_tab="login", login_email=email)

    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
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

    register_data = {
        "full_name": full_name,
        "email": email,
        "role": role,
        "department": department,
        "batch": batch,
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

    if role not in VALID_ROLES:
        messages.error(request, "Please select a valid account role.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    try:
        user_doc, error = register_user(
            full_name=full_name,
            email=email,
            password=password,
            role=role,
            department=department,
            batch=batch,
        )
    except Exception:
        messages.error(request, "Unable to complete registration right now. Please try again.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    if error or user_doc is None:
        messages.error(request, error or "Registration failed.")
        return _render_auth(request, active_tab="register", register_data=register_data)

    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    display_name = session_user["full_name"] or session_user["email"]
    messages.success(request, f"Account created! Welcome, {display_name}.")
    return redirect(get_dashboard_route(session_user["role"]))


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
