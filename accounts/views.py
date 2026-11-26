import time
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.debug import sensitive_post_parameters
from accounts.public_data import get_public_landing_showcase
from accounts.services import SELF_REGISTER_ROLES, VALID_ROLES, authenticate_user, create_public_contact_ticket, get_public_admin_contact, get_public_portal_metrics, list_approved_teachers, register_user, serialize_session_user
from core.db import get_cached, predictions_col, users_col
from core.decorators import get_dashboard_route
from core.theme_services import sync_theme_prefs_on_login


def root_redirect(request):
    user = request.session.get("user")
    if isinstance(user, dict):
        role = str(user.get("role") or "").strip().upper()
        if role in VALID_ROLES:
            return redirect(get_dashboard_route(role))
    return render(
        request,
        "public/landing.html",
        {
            "page_title": "Academic Performance & Early-Alert Portal",
            "metrics": get_public_portal_metrics(),
            "landing_showcase": get_public_landing_showcase(),
        },
    )


def about_view(request):
    return render(request, "public/about.html", {"page_title": "About EduPredict", "metrics": get_public_portal_metrics(), "admin_contact": get_public_admin_contact()})


def contact_view(request):
    form_data = {}
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip().lower()
        subject = (request.POST.get("subject") or "").strip()
        message = (request.POST.get("message") or "").strip()
        form_data = {"name": name, "email": email, "subject": subject, "message": message}
        if not name or not subject or not message:
            messages.error(request, "Name, subject, and message are required.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.")
            else:
                ticket_doc, error = create_public_contact_ticket(name, email, subject, message)
                if error or ticket_doc is None:
                    messages.error(request, error or "Unable to submit your inquiry right now.")
                else:
                    messages.success(request, f"Inquiry {ticket_doc['ticket_id']} received. Our admin team will review it shortly.")
                    return redirect("accounts:contact_view")
    return render(request, "public/contact.html", {"page_title": "Contact & Support", "admin_contact": get_public_admin_contact(), "form_data": form_data})


def _get_live_stats():
    def _fetch():
        try:
            col = predictions_col()
            cnt = int(col.estimated_document_count())
            if cnt <= 0:
                cnt = int(col.count_documents({}))
            return {"predictions_count": max(cnt, 0)}
        except Exception:
            return {"predictions_count": 0}
    return get_cached("auth:live_stats", _fetch, ttl=60.0)


def _render_auth(request, active_tab="login", login_email="", register_data=None, pending_teacher_approval=False):
    stats = _get_live_stats()
    return render(request, "accounts/auth.html", {"page_title": "Sign In & Registration", "active_tab": active_tab, "login_email": login_email, "register_data": register_data or {}, "approved_teachers": list_approved_teachers(), "live_predictions_count": stats.get("predictions_count", 0), "pending_teacher_approval": bool(pending_teacher_approval)})


def _handle_login(request):
    identifier = (request.POST.get("email") or "").strip()
    password = request.POST.get("password") or ""
    if not identifier or not password:
        messages.error(request, "Email or Student ID and password are required.")
        return _render_auth(request, active_tab="login", login_email=identifier)
    try:
        user_doc, error = authenticate_user(identifier, password)
    except Exception:
        time.sleep(0.05)
        messages.error(request, "Unable to connect to the database. Please try again.")
        return _render_auth(request, active_tab="login", login_email=identifier)
    if error or user_doc is None:
        time.sleep(0.05)
        messages.error(request, error or "Invalid email/student ID or password.")
        return _render_auth(request, active_tab="login", login_email=identifier)
    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    sync_theme_prefs_on_login(request, user_doc)
    messages.success(request, f"Welcome back, {session_user['full_name'] or session_user['email']}!")
    return redirect(get_dashboard_route(session_user["role"]))


def _handle_register(request):
    full_name, email = (request.POST.get("full_name") or "").strip(), (request.POST.get("email") or "").strip().lower()
    password, confirm_password = request.POST.get("password") or "", request.POST.get("confirm_password") or ""
    role, department, batch = (request.POST.get("role") or "").strip().upper(), (request.POST.get("department") or "").strip(), (request.POST.get("batch") or "").strip()
    program_level, phone, bio = (request.POST.get("program_level") or "").strip(), (request.POST.get("phone") or "").strip(), (request.POST.get("bio") or "").strip()
    assigned_teacher_id = (request.POST.get("assigned_teacher_id") or "").strip()
    register_data = {"full_name": full_name, "email": email, "role": role, "department": department, "batch": batch, "program_level": program_level, "phone": phone, "bio": bio, "assigned_teacher_id": assigned_teacher_id}
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
    if role == "STUDENT" and not assigned_teacher_id:
        messages.error(request, "Please select an approved Teacher for your class.")
        return _render_auth(request, active_tab="register", register_data=register_data)
    try:
        user_doc, error = register_user(full_name=full_name, email=email, password=password, role=role, department=department, batch=batch, phone=phone, bio=bio, program_level=program_level, assigned_teacher_id=assigned_teacher_id)
    except Exception:
        messages.error(request, "Unable to complete registration right now. Please try again.")
        return _render_auth(request, active_tab="register", register_data=register_data)
    if error or user_doc is None:
        messages.error(request, error or "Registration failed.")
        return _render_auth(request, active_tab="register", register_data=register_data)
    if str(user_doc.get("approval_status") or "").strip().upper() == "PENDING":
        role_label = "student" if role == "STUDENT" else "teacher"
        request.session["pending_approval"] = {"user_id": user_doc.get("user_id"), "email": email, "full_name": full_name, "role": role}
        messages.warning(request, f"Your {role_label} account was created and is waiting for Admin approval. This page will sign you in automatically once approved.")
        return _render_auth(request, active_tab="login", login_email=email, pending_teacher_approval=True)
    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    sync_theme_prefs_on_login(request, user_doc)
    messages.success(request, f"Account created! Welcome, {session_user['full_name'] or session_user['email']}.")
    return redirect(get_dashboard_route(session_user["role"]))


def _complete_pending_login(request, user_doc):
    request.session.pop("pending_approval", None)
    session_user = serialize_session_user(user_doc)
    request.session["user"] = session_user
    sync_theme_prefs_on_login(request, user_doc)
    messages.success(request, f"Account approved! Welcome, {session_user['full_name'] or session_user['email']}.")
    return get_dashboard_route(session_user["role"])


def _fetch_pending_state(request):
    pending = request.session.get("pending_approval")
    if not isinstance(pending, dict) or not pending.get("user_id"):
        return "NONE", None, ""
    try:
        user_doc = users_col().find_one({"user_id": pending.get("user_id")})
    except Exception:
        return "PENDING", None, pending.get("email", "")
    if not user_doc:
        request.session.pop("pending_approval", None)
        return "NONE", None, ""
    status = str(user_doc.get("approval_status") or "").strip().upper()
    if user_doc.get("is_active") and status != "PENDING":
        return "APPROVED", user_doc, pending.get("email", "")
    if status == "REJECTED":
        request.session.pop("pending_approval", None)
        return "REJECTED", user_doc, pending.get("email", "")
    return "PENDING", user_doc, pending.get("email", "")


@sensitive_post_parameters("password", "confirm_password")
def auth_view(request):
    user = request.session.get("user")
    if request.method == "GET" and isinstance(user, dict):
        role = str(user.get("role") or "").strip().upper()
        if role in VALID_ROLES:
            return redirect(get_dashboard_route(role))
    if request.method == "GET" and request.GET.get("reset_pending") == "1":
        request.session.pop("pending_approval", None)
        return redirect("accounts:auth_view")
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "login":
            return _handle_login(request)
        if action == "register":
            return _handle_register(request)
        messages.error(request, "Unsupported authentication request.")
        return _render_auth(request, active_tab="login")
    state, user_doc, pending_email = _fetch_pending_state(request)
    if state == "APPROVED":
        return redirect(_complete_pending_login(request, user_doc))
    if state == "REJECTED":
        reason = str((user_doc or {}).get("rejection_reason") or "Please contact your administrator.").strip()
        messages.error(request, f"Teacher approval request was declined: {reason}")
        return _render_auth(request, active_tab="login", login_email=pending_email)
    if state == "PENDING":
        return _render_auth(request, active_tab="login", login_email=pending_email, pending_teacher_approval=True)
    requested_tab = (request.GET.get("tab") or "").strip().lower()
    return _render_auth(request, active_tab="register" if requested_tab == "register" else "login")


def approval_status_view(request):
    state, user_doc, _ = _fetch_pending_state(request)
    if state == "APPROVED":
        return JsonResponse({"status": "APPROVED", "redirect_url": reverse(_complete_pending_login(request, user_doc))})
    if state == "REJECTED":
        return JsonResponse({"status": "REJECTED", "reason": str((user_doc or {}).get("rejection_reason") or "").strip()})
    return JsonResponse({"status": state})


def logout_view(request):
    request.session.flush()
    messages.info(request, "You have been signed out successfully.")
    return redirect("accounts:auth_view")


def error_404(request, exception=None):
    session = getattr(request, "session", None)
    user = session.get("user") if session is not None else None
    active_role = user.get("role") if isinstance(user, dict) else None
    return render(request, "404.html", {"page_title": "Page Not Found", "active_role": active_role}, status=404)
