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
from panels.teacher_alert_services import clean_teacher_student_cards, get_teacher_portal_meta, toggle_teacher_auto_alerts
from panels.teacher_services import (
    delete_student_record, get_teacher_alerts_context, get_teacher_dashboard_context,
    get_teacher_ingest_context, get_teacher_students_context, notify_all_high_risk_students,
    provision_student_accounts, reply_teacher_feedback, send_student_alert, update_student_record_inline,
)


def _param(request, key, default=""):
    return str(request.POST.get(key) or request.GET.get(key) or default).strip()


def _actor_label(request):
    user = request.session.get("user") or {}
    return str(user.get("full_name") or user.get("email") or "Teacher").strip()


def _actor_user_id(request):
    return str((request.session.get("user") or {}).get("user_id") or "").strip()


def _flash(request, ok, err, success_msg):
    if err or not ok:
        messages.error(request, err or "Action failed.")
    else:
        messages.success(request, success_msg)


def _handle_common_post(request):
    action = _param(request, "action").lower()
    user = request.session.get("user") or {}
    if action in ("update_student", "manual_entry", "update_marks"):
        doc, err = update_student_record_inline(request.POST, teacher_user=user)
        _flash(request, doc is not None, err, f"Saved marks for {doc['full_name']} ({doc['student_id']}) and updated predictions." if doc else "")
        return True
    if action == "send_alert":
        sev = _param(request, "severity") or _param(request, "urgency", "WARNING")
        doc, err = send_student_alert(_param(request, "student_id"), _param(request, "full_name"), _param(request, "course_code"), sev, request.POST.get("message") or request.POST.get("message_text"), _actor_label(request))
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
        sent_count, err = notify_all_high_risk_students(_actor_label(request), sender_user_id=_actor_user_id(request), teacher_user=user)
        _flash(request, sent_count > 0, err, f"Sent alerts to {sent_count} high-risk / low-attendance student(s).")
        return True
    if action == "toggle_auto_alerts":
        state, err = toggle_teacher_auto_alerts(_param(request, "enabled") == "1", _actor_label(request))
        _flash(request, err is None, err, f"Auto-alerts below 75% attendance {'enabled' if state else 'paused'}.")
        return True
    if action in ("reply_feedback", "resolve_feedback"):
        tid = _param(request, "ticket_id")
        reply_txt = _param(request, "reply_text") or ("Resolved by teacher." if action == "resolve_feedback" else "")
        ok, err = reply_teacher_feedback(tid, reply_txt, teacher_user=user, resolve_ticket=True)
        _flash(request, ok, err, f"Reply sent and ticket {tid} marked resolved.")
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

    user = request.session.get("user") or {}
    context = {
        "page_title": "Class Home", "active_role": "TEACHER",
        "kpis": {"total_students": 0, "avg_attendance": 0.0, "avg_marks": 0.0, "at_risk_count": 0, "courses_count": 0},
        "chart_data": {"course_summary": {"labels": [], "attendance": [], "marks": []}, "badge_breakdown": {"labels": ["Excellent", "Stable", "Needs Help", "High Risk"], "counts": [0, 0, 0, 0]}},
        "at_risk_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "at_risk_rows": [],
        "assigned_courses": [], "course_scope": "ALL", "my_courses_count": 0, "all_courses_count": 0,
        "admin_contact": {"name": "Portal Admin", "email": "admin@edupredict.edu"}, "db_error": None,
    }
    try:
        context.update(get_teacher_dashboard_context(teacher_user=user))
        context.update(get_teacher_portal_meta(user, course_scope=_param(request, "scope", "AUTO").upper()))
    except Exception as exc:
        context["db_error"] = str(exc)
    return render(request, "panels/teacher_dashboard.html", context)


@role_required(["TEACHER", "ADMIN"])
def teacher_students(request):
    user = request.session.get("user") or {}
    batch_f, course_f, status_f = _param(request, "batch", "ALL") or "ALL", _param(request, "course_code") or _param(request, "course") or "ALL", _param(request, "status", "ALL") or "ALL"
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                messages.error(request, "Unknown student action.")
        except Exception as exc:
            messages.error(request, f"Student update failed: {exc}")
        params = {k: v for k, v in (("batch", batch_f), ("course_code", course_f), ("status", status_f)) if v and v != "ALL"}
        target = reverse("panels:teacher_students")
        return redirect(f"{target}?{urlencode(params)}" if params else target)

    data = {"filter_options": {"batches": [], "courses": [], "statuses": ["Excellent", "Stable", "Needs Help", "High Risk"]}, "student_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "Pred GPA", "Status", "Actions"], "student_rows": [], "export_rows": [], "birth_map": {}}
    db_error = None
    try:
        data = get_teacher_students_context(batch_f, course_f, status_f, teacher_user=user)
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
        "page_title": "Student List", "active_role": "TEACHER", "filter_options": data["filter_options"],
        "selected_filters": {"batch": batch_f, "course_code": course_f, "course": course_f, "status": status_f},
        "student_headers": data["student_headers"], "student_rows": data["student_rows"], "birth_map": data.get("birth_map") or {},
        "student_cards": clean_teacher_student_cards(build_teacher_student_cards(data.get("students_raw"), fallback_rows=data.get("student_rows"), include_alert=True, include_delete=True)),
        "db_error": db_error,
    })


@role_required(["TEACHER", "ADMIN"])
def teacher_roster_pdf(request):
    user = request.session.get("user") or {}
    batch_f, course_f, status_f = _param(request, "batch", "ALL") or "ALL", _param(request, "course_code") or _param(request, "course") or "ALL", _param(request, "status", "ALL") or "ALL"
    try:
        data = get_teacher_students_context(batch_f, course_f, status_f, teacher_user=user)
    except Exception as exc:
        messages.error(request, f"Roster PDF generation failed: {exc}")
        return redirect("panels:teacher_students")
    response = HttpResponse(generate_teacher_roster_pdf(data), content_type="application/pdf")
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

    data = {"kpis": {"at_risk_count": 0, "high_risk_count": 0, "medium_risk_count": 0, "alerts_sent": 0, "unread_alerts": 0, "open_feedback_count": 0}, "roster_headers": ["Student ID", "Name", "Course", "Attendance", "Marks", "Status", "Actions"], "roster_rows": [], "history_headers": ["Title", "Student", "Message", "Level", "Read", "Date"], "history_rows": [], "feedback_headers": ["Ticket", "Student", "Subject", "Message", "Status", "Date", "Actions"], "feedback_rows": [], "students_picker": [], "auto_alerts_enabled": True, "high_risk_only_count": 0}
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
        writer.writerow(["student_id", "full_name", "course_code", "marks", "attendance", "birth_date"])
        writer.writerow(["STD-2026-001", "Ayesha Khan", "CS-101", "85", "90", "2004-05-14"])
        writer.writerow(["STD-2026-002", "Bilal Ahmed", "CS-101", "72", "80", "2003-11-22"])
        return response

    user = request.session.get("user") or {}
    if request.method == "POST":
        try:
            if not _handle_common_post(request):
                mode, actor = _param(request, "mode", "upload").lower(), _actor_label(request)
                if mode == "sample":
                    ingest_res = ingest_dataset(mode="sample", uploaded_by=actor, teacher_user=user)
                else:
                    file_obj = request.FILES.get("dataset_file")
                    if not file_obj:
                        messages.error(request, "Please select a .csv or .xlsx file first.")
                        return redirect("panels:teacher_ingest")
                    ingest_res = ingest_dataset(file_obj=file_obj, uploaded_by=actor, mode="upload", teacher_user=user)
                if ingest_res.get("status") != "COMPLETED":
                    messages.error(request, ingest_res.get("error") or "Upload failed.")
                else:
                    creds = provision_student_accounts(ingest_res.get("ingested_rows"), teacher_user=user)
                    if creds:
                        request.session["teacher_provisioned_creds"] = creds[:100]
                    ml_res = run_prediction_pipeline()
                    invalidate_cache()
                    cred_note = f" Created/updated {len(creds)} student login(s)." if creds else ""
                    messages.success(request, f"Saved {ingest_res.get('rows_processed', 0)} student rows and updated {ml_res.get('predictions_generated', 0)} predictions.{cred_note}")
        except Exception as exc:
            messages.error(request, f"Upload error: {exc}")
        return redirect("panels:teacher_ingest")

    data = {"roster_headers": ["Student ID", "Name", "Batch", "Course", "Attendance", "Marks", "GPA", "Actions"], "roster_rows": [], "log_headers": ["File Name", "Rows", "Fixed", "Status", "Uploaded"], "log_rows": [], "courses_list": ["CS-101"], "students_picker": [], "birth_map": {}, "required_columns": REQUIRED_COLUMNS}
    db_error = None
    try:
        data = get_teacher_ingest_context(teacher_user=user)
    except Exception as exc:
        db_error = str(exc)

    return render(request, "panels/teacher_ingest.html", {
        "page_title": "Upload Marks", "active_role": "TEACHER", **data,
        "provisioned_creds": request.session.pop("teacher_provisioned_creds", []),
        "roster_cards": clean_teacher_student_cards(build_teacher_student_cards(data.get("roster_raw"), fallback_rows=data.get("roster_rows"), include_alert=False, include_delete=True)),
        "db_error": db_error,
    })
