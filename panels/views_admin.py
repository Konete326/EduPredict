from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from core.decorators import get_dashboard_route, login_required_custom, role_required
from panels.admin_audit_services import VALID_LOG_CATEGORIES, clear_manual_audit_logs, export_activity_logs_csv, get_default_admin_logs_context, get_default_portal_settings_context, get_portal_settings, list_activity_logs, record_audit_log, reset_portal_settings, update_portal_settings
from panels.admin_seed import get_default_admin_overview_context
from panels.admin_services import build_backup_payload, build_course_table_data, build_ticket_table_data, build_user_table_data, create_course_record, create_ticket_record, create_user_record, delete_course_record, delete_ticket_record, delete_user_record, get_admin_overview_context, list_active_teachers, list_courses_with_stats, list_tickets, list_users, mark_notifications_read, reject_teacher_account, toggle_ticket_status, toggle_user_status, update_course_record, update_user_record
from panels.directory_card_services import build_admin_user_cards
from panels.notification_services import delete_ticket_reply, reply_to_ticket


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _actor_name(request):
    user = request.session.get("user") or {}
    return str(user.get("full_name") or user.get("email") or "System Admin").strip() or "System Admin"


def _redirect_with_filter(route_name, param_name, param_value):
    base_url, clean_val = reverse(route_name), str(param_value or "").strip()
    return redirect(f"{base_url}?{param_name}={clean_val}") if clean_val and clean_val != "ALL" else redirect(base_url)


def _flash_result(request, ok, error, success_msg):
    messages.error(request, error or "Operation could not be completed.") if (error or not ok) else messages.success(request, success_msg)


def _download_response(content, content_type, filename):
    resp = HttpResponse(content, content_type=content_type)
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp


@role_required(["ADMIN"])
def admin_dashboard(request):
    context = {"page_title": "Admin Home", "active_role": "ADMIN", "db_error": None, **get_default_admin_overview_context()}
    try:
        context.update(get_admin_overview_context())
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/admin_dashboard.html", context)


@role_required(["ADMIN"])
def admin_users(request):
    filter_role = (_param(request, "filter_role") or _param(request, "role") or "ALL").upper()
    session_user = request.session.get("user") or {}
    actor_id, actor_email = str(session_user.get("user_id") or "").strip(), str(session_user.get("email") or "").strip().lower()
    if request.method == "POST":
        action, user_id, full_name, actor = _param(request, "action").lower(), _param(request, "user_id"), request.POST.get("full_name") or request.POST.get("name"), _actor_name(request)
        try:
            if action == "create":
                created, err = create_user_record(full_name, request.POST.get("email"), request.POST.get("password"), request.POST.get("role"), request.POST.get("department"), request.POST.get("batch"), actor_name=actor, program_level=request.POST.get("program_level") or "")
                _flash_result(request, created is not None, err, f"User {created['full_name']} ({created['user_id']}) created." if created else "")
            elif action == "update":
                ok, err = update_user_record(user_id, full_name, request.POST.get("email"), request.POST.get("role"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("password") or "", actor_user_id=actor_id, actor_email=actor_email, actor_name=actor, program_level=request.POST.get("program_level"))
                _flash_result(request, ok, err, f"User {user_id} updated.")
            elif action == "toggle":
                new_state, err = toggle_user_status(user_id, actor_user_id=actor_id, actor_email=actor_email, actor_name=actor)
                _flash_result(request, new_state is not None, err, f"User {user_id} {'activated' if new_state else 'deactivated'}.")
            elif action == "reject":
                ok, err = reject_teacher_account(user_id, request.POST.get("rejection_reason") or request.POST.get("reason"), actor_user_id=actor_id, actor_email=actor_email, actor_name=actor)
                _flash_result(request, ok, err, f"Teacher request {user_id} rejected.")
            elif action == "delete":
                ok, err = delete_user_record(user_id, actor_user_id=actor_id, actor_email=actor_email, actor_name=actor)
                _flash_result(request, ok, err, f"User {user_id} deleted.")
            else:
                messages.error(request, "Unknown user action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return _redirect_with_filter("panels:admin_users", "role", filter_role)
    users, role_counts, db_error = [], {"ALL": 0, "ADMIN": 0, "TEACHER": 0, "STUDENT": 0, "ANALYST": 0, "PENDING": 0, "REJECTED": 0}, None
    try:
        users, role_counts = list_users(filter_role)
    except Exception as exc:
        db_error = str(exc)
    user_headers, user_rows = build_user_table_data(users, filter_role, actor_id, actor_email=actor_email)
    user_cards = build_admin_user_cards(users, filter_role, actor_id, actor_email=actor_email)
    return render(request, "panels/admin_users.html", {"page_title": "Users", "active_role": "ADMIN", "users": users, "user_headers": user_headers, "user_rows": user_rows, "user_cards": user_cards, "role_counts": role_counts, "selected_role": filter_role, "db_error": db_error})


@role_required(["ADMIN"])
def admin_courses(request):
    filter_dept = _param(request, "filter_dept") or _param(request, "department") or "ALL"
    if request.method == "POST":
        action, code, actor = _param(request, "action").lower(), _param(request, "course_code").upper(), _actor_name(request)
        try:
            if action == "create":
                created, err = create_course_record(code, request.POST.get("title"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("instructor"), request.POST.get("credits"), request.POST.get("capacity"), request.POST.get("status") or "ACTIVE", actor_name=actor, instructor_id=request.POST.get("instructor_id") or "", instructor_email=request.POST.get("instructor_email") or "", program_level=request.POST.get("program_level") or "")
                _flash_result(request, created is not None, err, f"Course {created['course_code']} added." if created else "")
            elif action == "update":
                ok, err = update_course_record(code, request.POST.get("title"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("instructor"), request.POST.get("credits"), request.POST.get("capacity"), request.POST.get("status") or "ACTIVE", actor_name=actor, instructor_id=request.POST.get("instructor_id") or "", instructor_email=request.POST.get("instructor_email") or "", program_level=request.POST.get("program_level") or "")
                _flash_result(request, ok, err, f"Course {code} updated.")
            elif action == "delete":
                ok, err = delete_course_record(code, actor_name=actor)
                _flash_result(request, ok, err, f"Course {code} removed.")
            else:
                messages.error(request, "Unknown course action.")
        except Exception as exc:
            messages.error(request, f"Course error: {exc}")
        return _redirect_with_filter("panels:admin_courses", "department", filter_dept)
    courses, departments, dept_counts, teacher_options, db_error = [], [], {"ALL": 0}, [], None
    try:
        courses, departments, dept_counts = list_courses_with_stats(filter_dept)
        teacher_options = list_active_teachers()
    except Exception as exc:
        db_error = str(exc)
    course_headers, course_rows = build_course_table_data(courses, filter_dept)
    return render(request, "panels/admin_courses.html", {"page_title": "Courses", "active_role": "ADMIN", "courses": courses, "course_headers": course_headers, "course_rows": course_rows, "departments": departments, "dept_counts": dept_counts, "teacher_options": teacher_options, "selected_dept": filter_dept, "db_error": db_error})


@role_required(["ADMIN"])
def admin_tickets(request):
    filter_status = (_param(request, "filter_status") or _param(request, "status") or "ALL").upper()
    if request.method == "POST":
        action, ticket_id, actor = _param(request, "action").lower(), _param(request, "ticket_id"), _actor_name(request)
        try:
            if action == "toggle_status":
                new_status, err = toggle_ticket_status(ticket_id, actor_name=actor)
                _flash_result(request, new_status is not None, err, f"Ticket {ticket_id} marked as {new_status}.")
            elif action == "reply_ticket":
                resolve_flag = True if "resolve_ticket" not in request.POST else str(request.POST.get("resolve_ticket") or "").strip().lower() in ("1", "true", "yes", "on")
                ok, err = reply_to_ticket(ticket_id, request.POST.get("reply_text"), actor_name=actor, resolve_ticket=resolve_flag)
                _flash_result(request, ok, err, f"Reply sent for ticket {ticket_id}.")
            elif action == "delete_reply":
                ok, err = delete_ticket_reply(ticket_id, actor_name=actor)
                _flash_result(request, ok, err, f"Reply removed from ticket {ticket_id}.")
            elif action == "delete":
                ok, err = delete_ticket_record(ticket_id, actor_name=actor)
                _flash_result(request, ok, err, f"Ticket {ticket_id} deleted.")
            else:
                messages.error(request, "Unknown ticket action.")
        except Exception as exc:
            messages.error(request, f"Ticket error: {exc}")
        return _redirect_with_filter("panels:admin_tickets", "status", filter_status)
    tickets, status_counts, db_error = [], {"ALL": 0, "OPEN": 0, "RESOLVED": 0}, None
    try:
        tickets, status_counts = list_tickets(filter_status)
    except Exception as exc:
        db_error = str(exc)
    ticket_headers, ticket_rows = build_ticket_table_data(tickets, filter_status)
    return render(request, "panels/admin_tickets.html", {"page_title": "Help Tickets", "active_role": "ADMIN", "tickets": tickets, "ticket_headers": ticket_headers, "ticket_rows": ticket_rows, "status_counts": status_counts, "selected_status": filter_status, "db_error": db_error})


@role_required(["ADMIN"])
def admin_logs(request):
    raw_cat = (_param(request, "filter_category") or _param(request, "category") or "ALL").upper()
    selected_cat = raw_cat if raw_cat == "ALL" or raw_cat in VALID_LOG_CATEGORIES else "ALL"
    if request.method == "POST":
        action, actor = _param(request, "action").lower(), _actor_name(request)
        try:
            if action == "log_note":
                summary = str(request.POST.get("summary") or "").strip()
                created = record_audit_log(actor, "ADMIN", request.POST.get("category") or "SYSTEM", "MANUAL_NOTE", summary, severity=request.POST.get("severity") or "INFO", source="MANUAL") if summary else None
                _flash_result(request, created is not None, None if created else "Activity note summary is required.", f"Activity note {created['log_id']} saved." if created else "")
            elif action == "clear_custom":
                messages.success(request, f"Cleared {clear_manual_audit_logs(actor_name=actor)} manual activity note(s).")
            else:
                messages.error(request, "Unknown log action.")
        except Exception as exc:
            messages.error(request, f"Activity log error: {exc}")
        return _redirect_with_filter("panels:admin_logs", "category", selected_cat)
    if str(request.GET.get("export") or "").strip().lower() == "csv":
        try:
            return _download_response(*export_activity_logs_csv(selected_cat))
        except Exception as exc:
            messages.error(request, f"Log export failed: {exc}")
            return _redirect_with_filter("panels:admin_logs", "category", selected_cat)
    context = {"page_title": "Activity Logs", "active_role": "ADMIN", "db_error": None, **get_default_admin_logs_context(selected_cat)}
    try:
        logs, category_counts, log_kpis, log_headers, log_rows = list_activity_logs(selected_cat)
        context.update({"logs": logs, "category_counts": category_counts, "log_kpis": log_kpis, "log_headers": log_headers, "log_rows": log_rows})
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/admin_logs.html", context)


@role_required(["ADMIN"])
def admin_settings(request):
    if request.method == "POST":
        action, actor = _param(request, "action").lower(), _actor_name(request)
        try:
            if action == "save_settings":
                saved, err = update_portal_settings(request.POST, actor_name=actor)
                _flash_result(request, saved is not None, err, "Portal settings saved.")
            elif action == "reset_defaults":
                restored, err = reset_portal_settings(actor_name=actor)
                _flash_result(request, restored is not None, err, "Portal settings restored to defaults.")
            else:
                messages.error(request, "Unknown settings action.")
        except Exception as exc:
            messages.error(request, f"Settings error: {exc}")
        return redirect("panels:admin_settings")
    context = {"page_title": "Portal Settings", "active_role": "ADMIN", "db_error": None, **get_default_portal_settings_context()}
    try:
        context.update(get_portal_settings())
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/admin_settings.html", context)


@role_required(["ADMIN"])
def admin_backup_export(request):
    fmt = str(request.GET.get("format") or "json").strip().lower()
    try:
        return _download_response(*build_backup_payload(fmt=fmt if fmt in ("json", "csv") else "json"))
    except Exception as exc:
        messages.error(request, f"Backup export failed: {exc}")
        return redirect("panels:admin_dashboard")


@login_required_custom
def submit_support_ticket(request):
    user = request.session.get("user") or {}
    fallback_url, referer = reverse(get_dashboard_route(user.get("role"))), request.META.get("HTTP_REFERER", "")
    next_url = referer if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}) else fallback_url
    if str(user.get("role") or "").strip().upper() == "ADMIN":
        messages.warning(request, "Admins manage help tickets directly and cannot send tickets to themselves.")
        return redirect("panels:admin_tickets")
    if request.method != "POST":
        return redirect(next_url)
    try:
        files = request.FILES.getlist("attachments")
        urls = [u.strip() for u in request.POST.getlist("attachment_urls") if u.strip()]
        created, err = create_ticket_record(user.get("user_id", ""), user.get("full_name") or user.get("email") or "Portal User", user.get("role") or "USER", request.POST.get("subject"), request.POST.get("message"), attachments=(urls + files)[:3])
        _flash_result(request, created is not None, err, f"Help ticket {created['ticket_id']} sent to Admin." if created else "")
    except Exception as exc:
        messages.error(request, f"Could not send help ticket: {exc}")
    return redirect(next_url)


@login_required_custom
def mark_notifications_read_view(request):
    user = request.session.get("user") or {}
    if request.method != "POST":
        return redirect(get_dashboard_route(user.get("role")))
    try:
        user_payload = {"user_id": str(user.get("user_id") or "").strip(), "student_id": str(user.get("student_id") or "").strip(), "role": str(user.get("role") or "").strip().upper()}
        return JsonResponse({"ok": True, "updated": mark_notifications_read(user_payload)})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
