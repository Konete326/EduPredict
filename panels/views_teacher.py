import csv
from urllib.parse import urlencode
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from analytics.data_pipeline import REQUIRED_COLUMNS, ingest_dataset
from analytics.ml_engine import run_prediction_pipeline
from core.db import invalidate_cache, notifications_col
from core.decorators import role_required
from panels.directory_card_services import build_teacher_student_cards
from panels.pdf_services import generate_teacher_roster_pdf
from panels.teacher_alert_services import (
    clean_teacher_student_cards, get_teacher_alerts_context,
    get_teacher_portal_meta, notify_all_high_risk_students, toggle_teacher_auto_alerts,
)
from panels.teacher_services import (
    delete_student_record, get_teacher_dashboard_context, get_teacher_ingest_context,
    get_teacher_students_context, send_student_alert, update_student_record_inline,
)


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _active_role(request):
    user = request.session.get("user") or {}
    return str(user.get("role") or "TEACHER").strip().upper()


def _actor_label(request):
    user = request.session.get("user") or {}
    return str(user.get("full_name") or user.get("email") or "Teacher").strip()


def _actor_user_id(request):
    user = request.session.get("user") or {}
    return str(user.get("user_id") or "").strip()


def _flash(request, ok, err, success_msg):
    if err or not ok:
        messages.error(request, err or "Action failed.")
    else:
        messages.success(request, success_msg)


def _handle_common_post(request):
    action = _param(request, "action").lower()
    if action in ("update_student", "manual_entry", "update_marks"):
        doc, err = update_student_record_inline(request.POST)
        _flash(request, doc is not None, err, f"Saved marks for {doc['full_name']} ({doc['student_id']}) and updated predictions." if doc else "")
        return True
    if action == "send_alert":
        sev = _param(request, "severity") or _param(request, "urgency", "WARNING")
        doc, err = send_student_alert(
            _param(request, "student_id"), _param(request, "full_name"), _param(request, "course_code"),
            sev, request.POST.get("message") or request.POST.get("message_text"),
            _actor_label(request),
        )
        if doc and doc.get("_id") and _actor_user_id(request):
            notifications_col().update_one({"_id": doc["_id"]}, {"$set": {"sender_user_id": _actor_user_id(request)}})
        _flash(request, doc is not None, err, f"Alert sent to {_param(request, 'student_id')}." if doc else "")
        return True
    if action == "delete_student":
        sid = _param(request, "student_id")
        ok, err = delete_student_record(sid)
        _flash(request, ok, err, f"Removed student record {sid}.")
        return True
    if action == "notify_all_high_risk":
        sent_count, err = notify_all_high_risk_students(_actor_label(request), sender_user_id=_actor_user_id(request))
        _flash(request, sent_count > 0, err, f"Sent alerts to {sent_count} high-risk / low-attendance student(s).")
        return True
    if action == "toggle_auto_alerts":
        enabled_flag = _param(request, "enabled") == "1"
        state, err = toggle_teacher_auto_alerts(enabled_flag, _actor_label(request))
        _flash(request, err is None, err, f"Auto-alerts below 75% attendance {'enabled' if state else 'paused'}.")
        return True
    return False


@role_required(["TEACHER", "ADMIN"])
def teacher_dashboard(request):
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown action.")
        except Exception as exc:
            messages.error(request, f"Database error: {exc}")
        return redirect("panels:teacher_dashboard")

    course_scope = _param(request, "scope", "AUTO").upper()
    context = {
        "page_title": "Class Home",
        "active_role": "TEACHER",
        "kpis": {"total_students": 0, "avg_attendance": 0.0, "avg_marks": 0.0, "at_risk_count": 0, "courses_count": 0},
        "chart_data": {"course_summary": {"labels": [], "attendance": [], "marks": []}, "badge_breakdown": {"labels": ["Excellent", "Stable", "Needs Help", "High Risk"], "counts": [0, 0, 0, 0]}},
        "at_risk_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"],
        "at_risk_rows": [],
        "assigned_courses": [],
        "course_scope": "ALL",
        "my_courses_count": 0,
        "all_courses_count": 0,
        "admin_contact": {"name": "Portal Admin", "email": "admin@edupredict.edu"},
        "db_error": None,
    }
    try:
        context.update(get_teacher_dashboard_context())
        context.update(get_teacher_portal_meta(request.session.get("user"), course_scope=course_scope))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_dashboard.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_students(request):
    batch_f = _param(request, "batch", "ALL") or "ALL"
    course_f = _param(request, "course_code") or _param(request, "course") or "ALL"
    status_f = _param(request, "status", "ALL") or "ALL"

    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown student action.")
        except Exception as exc:
            messages.error(request, f"Student update failed: {exc}")
        params = {k: v for k, v in (("batch", batch_f), ("course_code", course_f), ("status", status_f)) if v and v != "ALL"}
        target = reverse("panels:teacher_students")
        return redirect(f"{target}?{urlencode(params)}" if params else target)

    data = {"filter_options": {"batches": [], "courses": [], "statuses": ["Excellent", "Stable", "Needs Help", "High Risk"]}, "student_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"], "student_rows": [], "export_rows": []}
    db_error = None
    try:
        data = get_teacher_students_context(batch_f, course_f, status_f)
    except Exception as exc:
        db_error = str(exc)

    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="edupredict_class_students.csv"'
        writer = csv.writer(response)
        writer.writerow(["student_id", "full_name", "batch", "course_code", "attendance_pct", "internal_marks", "predicted_gpa", "status"])
        for r in data["export_rows"]:
            writer.writerow([r["student_id"], r["full_name"], r["batch"], r["course_code"], r["attendance_pct"], r["internal_marks"], r["predicted_gpa"], r["status"]])
        return response

    return render(request, "panels/teacher_students.html", {
        "page_title": "Student List",
        "active_role": "TEACHER",
        "filter_options": data["filter_options"],
        "selected_filters": {"batch": batch_f, "course_code": course_f, "course": course_f, "status": status_f},
        "student_headers": data["student_headers"],
        "student_rows": data["student_rows"],
        "student_cards": clean_teacher_student_cards(build_teacher_student_cards(data.get("students_raw"), fallback_rows=data.get("student_rows"), include_alert=True, include_delete=True)),
        "db_error": db_error,
    })


@role_required(["TEACHER", "ADMIN"])
def teacher_roster_pdf(request):
    batch_f = _param(request, "batch", "ALL") or "ALL"
    course_f = _param(request, "course_code") or _param(request, "course") or "ALL"
    status_f = _param(request, "status", "ALL") or "ALL"
    try:
        data = get_teacher_students_context(batch_f, course_f, status_f)
    except Exception as exc:
        messages.error(request, f"Roster PDF generation failed: {exc}")
        return redirect("panels:teacher_students")
    pdf_bytes = generate_teacher_roster_pdf(data)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="edupredict_class_roster.pdf"'
    return response


@role_required(["TEACHER", "ADMIN"])
def teacher_alerts(request):
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown alert action.")
        except Exception as exc:
            messages.error(request, f"Alert error: {exc}")
        return redirect("panels:teacher_alerts")

    data = {"kpis": {"at_risk_count": 0, "high_risk_count": 0, "medium_risk_count": 0, "alerts_sent": 0, "unread_alerts": 0}, "roster_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "roster_rows": [], "history_headers": ["Title", "Student", "Message", "Level", "Read", "Date"], "history_rows": [], "students_picker": [], "auto_alerts_enabled": True, "high_risk_only_count": 0}
    db_error = None
    try:
        data = get_teacher_alerts_context(request.session.get("user"))
    except Exception as exc:
        db_error = str(exc)

    return render(request, "panels/teacher_alerts.html", {"page_title": "Risk Alerts", "active_role": "TEACHER", **data, "db_error": db_error})


@role_required(["TEACHER", "ADMIN"])
def teacher_ingest(request):
    if request.GET.get("template") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="edupredict_marks_template.csv"'
        writer = csv.writer(response)
        writer.writerow(["student_id", "full_name", "course_code", "marks", "attendance"])
        writer.writerow(["STD-2026-001", "Ayesha Khan", "CS-101", "85", "90"])
        writer.writerow(["STD-2026-002", "Bilal Ahmed", "CS-101", "72", "80"])
        return response

    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                mode = _param(request, "mode", "upload").lower()
                actor = _actor_label(request)
                if mode == "sample":
                    ingest_res = ingest_dataset(mode="sample", uploaded_by=actor)
                else:
                    file_obj = request.FILES.get("dataset_file")
                    if not file_obj:
                        messages.error(request, "Please select a .csv or .xlsx file first.")
                        return redirect("panels:teacher_ingest")
                    ingest_res = ingest_dataset(file_obj=file_obj, uploaded_by=actor, mode="upload")
                if ingest_res.get("status") != "COMPLETED":
                    messages.error(request, ingest_res.get("error") or "Upload failed.")
                else:
                    ml_res = run_prediction_pipeline()
                    invalidate_cache()
                    messages.success(request, f"Saved {ingest_res.get('rows_processed', 0)} student rows ({ingest_res.get('missing_values_fixed', 0)} blanks fixed) and updated {ml_res.get('predictions_generated', 0)} predictions.")
        except Exception as exc:
            messages.error(request, f"Upload error: {exc}")
        return redirect("panels:teacher_ingest")

    data = {"roster_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "GPA", "Actions"], "roster_rows": [], "log_headers": ["File Name", "Rows", "Fixed", "Status", "Uploaded"], "log_rows": [], "courses_list": ["CS-101"], "required_columns": REQUIRED_COLUMNS}
    db_error = None
    try:
        data = get_teacher_ingest_context()
    except Exception as exc:
        db_error = str(exc)

    return render(request, "panels/teacher_ingest.html", {
        "page_title": "Upload Marks",
        "active_role": "TEACHER",
        **data,
        "roster_cards": clean_teacher_student_cards(build_teacher_student_cards(data.get("roster_raw"), fallback_rows=data.get("roster_rows"), include_alert=False, include_delete=True)),
        "db_error": db_error,
    })
