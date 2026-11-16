from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from core.decorators import get_dashboard_route, login_required_custom, role_required
from panels.admin_services import (
    build_backup_payload, build_course_table_data, build_ticket_table_data, build_user_table_data,
    create_course_record, create_ticket_record, create_user_record, delete_course_record,
    delete_ticket_record, delete_user_record, get_admin_overview_context, list_courses_with_stats,
    list_tickets, list_users, mark_notifications_read, toggle_ticket_status,
    toggle_user_status, update_course_record, update_user_record,
)


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _redirect_with_filter(route_name, param_name, param_value):
    base_url = reverse(route_name)
    clean_val = str(param_value or "").strip()
    if clean_val and clean_val != "ALL":
        return redirect(f"{base_url}?{param_name}={clean_val}")
    return redirect(base_url)


def _flash_result(request, ok, error, success_msg):
    if error or not ok:
        messages.error(request, error or "Operation could not be completed.")
    else:
        messages.success(request, success_msg)


@role_required(["ADMIN"])
def admin_dashboard(request):
    context = {
        "page_title": "Admin Home",
        "active_role": "ADMIN",
        "kpis": {
            "total_students": 0, "student_accounts": 0, "active_teachers": 0,
            "high_risk_count": 0, "total_predictions": 0, "total_users": 0,
            "active_users": 0, "open_tickets": 0, "total_tickets": 0,
            "total_courses": 0, "active_courses": 0, "datasets_count": 0,
            "unread_alerts": 0, "avg_attendance": 0.0, "system_status": "Offline",
        },
        "chart_data": {
            "departments": {"labels": [], "enrolled": [], "capacity": []},
            "risk_breakdown": {"labels": ["Low Risk", "Medium Risk", "High Risk"], "counts": [0, 0, 0]},
        },
        "recent_tickets": [],
        "recent_ticket_headers": ["Ticket ID", "User", "Subject", "Status", "Date"],
        "recent_ticket_rows": [],
        "db_error": None,
    }
    try:
        context.update(get_admin_overview_context())
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/admin_dashboard.html", context)


@role_required(["ADMIN"])
def admin_users(request):
    filter_role = (_param(request, "filter_role") or _param(request, "role") or "ALL").upper()
    session_user = request.session.get("user") or {}
    actor_id = str(session_user.get("user_id") or "").strip()
    actor_email = str(session_user.get("email") or "").strip().lower()
    if request.method == "POST":
        action = _param(request, "action").lower()
        user_id = _param(request, "user_id")
        full_name = request.POST.get("full_name") or request.POST.get("name")
        try:
            if action == "create":
                created, err = create_user_record(full_name, request.POST.get("email"), request.POST.get("password"), request.POST.get("role"), request.POST.get("department"), request.POST.get("batch"))
                _flash_result(request, created is not None, err, f"User {created['full_name']} ({created['user_id']}) created." if created else "")
            elif action == "update":
                ok, err = update_user_record(user_id, full_name, request.POST.get("email"), request.POST.get("role"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("password") or "", actor_user_id=actor_id, actor_email=actor_email)
                _flash_result(request, ok, err, f"User {user_id} updated.")
            elif action == "toggle":
                new_state, err = toggle_user_status(user_id, actor_user_id=actor_id, actor_email=actor_email)
                _flash_result(request, new_state is not None, err, f"User {user_id} {'activated' if new_state else 'deactivated'}.")
            elif action == "delete":
                ok, err = delete_user_record(user_id, actor_user_id=actor_id, actor_email=actor_email)
                _flash_result(request, ok, err, f"User {user_id} deleted.")
            else:
                messages.error(request, "Unknown user action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return _redirect_with_filter("panels:admin_users", "role", filter_role)

    users, role_counts, db_error = [], {"ALL": 0, "ADMIN": 0, "TEACHER": 0, "STUDENT": 0, "ANALYST": 0}, None
    try:
        users, role_counts = list_users(filter_role)
    except Exception as exc:
        db_error = str(exc)
    user_headers, user_rows = build_user_table_data(users, filter_role, actor_id, actor_email=actor_email)
    return render(request, "panels/admin_users.html", {
        "page_title": "Users",
        "active_role": "ADMIN",
        "users": users,
        "user_headers": user_headers,
        "user_rows": user_rows,
        "role_counts": role_counts,
        "selected_role": filter_role,
        "db_error": db_error,
    })


@role_required(["ADMIN"])
def admin_courses(request):
    filter_dept = _param(request, "filter_dept") or _param(request, "department") or "ALL"
    if request.method == "POST":
        action = _param(request, "action").lower()
        code = _param(request, "course_code").upper()
        try:
            if action == "create":
                created, err = create_course_record(code, request.POST.get("title"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("instructor"), request.POST.get("credits"), request.POST.get("capacity"), request.POST.get("status") or "ACTIVE")
                _flash_result(request, created is not None, err, f"Course {created['course_code']} added." if created else "")
            elif action == "update":
                ok, err = update_course_record(code, request.POST.get("title"), request.POST.get("department"), request.POST.get("batch"), request.POST.get("instructor"), request.POST.get("credits"), request.POST.get("capacity"), request.POST.get("status") or "ACTIVE")
                _flash_result(request, ok, err, f"Course {code} updated.")
            elif action == "delete":
                ok, err = delete_course_record(code)
                _flash_result(request, ok, err, f"Course {code} removed.")
            else:
                messages.error(request, "Unknown course action.")
        except Exception as exc:
            messages.error(request, f"Course error: {exc}")
        return _redirect_with_filter("panels:admin_courses", "department", filter_dept)

    courses, departments, dept_counts, db_error = [], [], {"ALL": 0}, None
    try:
        courses, departments, dept_counts = list_courses_with_stats(filter_dept)
    except Exception as exc:
        db_error = str(exc)
    course_headers, course_rows = build_course_table_data(courses, filter_dept)
    return render(request, "panels/admin_courses.html", {
        "page_title": "Courses",
        "active_role": "ADMIN",
        "courses": courses,
        "course_headers": course_headers,
        "course_rows": course_rows,
        "departments": departments,
        "dept_counts": dept_counts,
        "selected_dept": filter_dept,
        "db_error": db_error,
    })


@role_required(["ADMIN"])
def admin_tickets(request):
    filter_status = (_param(request, "filter_status") or _param(request, "status") or "ALL").upper()
    if request.method == "POST":
        action = _param(request, "action").lower()
        ticket_id = _param(request, "ticket_id")
        try:
            if action == "toggle_status":
                new_status, err = toggle_ticket_status(ticket_id)
                _flash_result(request, new_status is not None, err, f"Ticket {ticket_id} marked as {new_status}.")
            elif action == "delete":
                ok, err = delete_ticket_record(ticket_id)
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
    return render(request, "panels/admin_tickets.html", {
        "page_title": "Help Tickets",
        "active_role": "ADMIN",
        "tickets": tickets,
        "ticket_headers": ticket_headers,
        "ticket_rows": ticket_rows,
        "status_counts": status_counts,
        "selected_status": filter_status,
        "db_error": db_error,
    })


@role_required(["ADMIN"])
def admin_backup_export(request):
    fmt = str(request.GET.get("format") or "json").strip().lower()
    fmt = fmt if fmt in ("json", "csv") else "json"
    try:
        content, content_type, filename = build_backup_payload(fmt=fmt)
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as exc:
        messages.error(request, f"Backup export failed: {exc}")
        return redirect("panels:admin_dashboard")


@login_required_custom
def submit_support_ticket(request):
    user = request.session.get("user") or {}
    fallback_url = reverse(get_dashboard_route(user.get("role")))
    referer = request.META.get("HTTP_REFERER", "")
    next_url = referer if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}) else fallback_url
    if str(user.get("role") or "").strip().upper() == "ADMIN":
        messages.warning(request, "Admins manage help tickets directly and cannot send tickets to themselves.")
        return redirect("panels:admin_tickets")
    if request.method != "POST":
        return redirect(next_url)
    try:
        created, err = create_ticket_record(user.get("user_id", ""), user.get("full_name") or user.get("email") or "Portal User", user.get("role") or "USER", request.POST.get("subject"), request.POST.get("message"))
        _flash_result(request, created is not None, err, f"Help ticket {created['ticket_id']} sent to Admin." if created else "")
    except Exception as exc:
        messages.error(request, f"Could not send help ticket: {exc}")
    return redirect(next_url)


@login_required_custom
def mark_notifications_read_view(request):
    if request.method != "POST":
        user = request.session.get("user") or {}
        return redirect(get_dashboard_route(user.get("role")))
    try:
        updated = mark_notifications_read(request.session.get("user") or {})
        return JsonResponse({"ok": True, "updated": updated})
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
