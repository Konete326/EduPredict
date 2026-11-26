import csv
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from core.decorators import role_required
from panels.admin_services import mark_notifications_read
from panels.notification_services import submit_student_feedback
from panels.pdf_services import _resolve_pdf_branding, generate_student_report_card_pdf
from panels.student_services import (
    build_report_export_rows,
    get_student_alerts_context,
    get_student_overview_context,
    list_student_feedback_tickets,
    mark_alert_read,
    resolve_assigned_teacher,
)


def _student_identity(request):
    user = request.session.get("user") or {}
    role = str(user.get("role") or "STUDENT").strip().upper()
    student_id = str(user.get("student_id") or "").strip()
    user_id = str(user.get("user_id") or "").strip()
    if not student_id:
        student_id = user_id
    return student_id, user_id, role, user


def _empty_overview_context():
    return {
        "record": {
            "student_id": "", "full_name": "", "batch": "", "department": "", "program_level": "",
            "courses": [], "avg_attendance": 0.0, "avg_marks": 0.0, "avg_assignment": 0.0,
            "lms_hours_weekly": 0.0, "previous_gpa": 0.0, "predicted_gpa": None,
            "risk_level": "PENDING", "risk_score": None, "is_anomaly": False,
            "anomaly_reason": "", "recommendation": "", "generated_at": None,
        },
        "subject_rows": [],
        "chart": {"labels": [], "mine": [], "class_avg": []},
        "rank": None,
        "tips": [],
        "insight": {"summary": "Prediction data is unavailable right now.", "status": "info", "points": []},
        "unread_alerts": 0,
        "active_courses": 0,
        "credits": 0.0,
        "teacher_alerts": [],
        "enrolled_courses": [],
        "admin_contact": {"name": "", "email": ""},
        "assigned_teacher": {"teacher_id": "", "name": "", "email": ""},
        "alerts": [],
        "my_tickets": [],
        "unread": 0,
        "total": 0,
    }


def _safe_context(loader, *args):
    try:
        return loader(*args), None
    except Exception as exc:
        return _empty_overview_context(), str(exc)


def _risk_status(risk_level):
    risk = str(risk_level or "").upper()
    return {"HIGH": "danger", "MEDIUM": "warning", "PENDING": "info"}.get(risk, "success")


def _build_subject_table_rows(subject_rows):
    headers = ["Course", "My Marks", "Class Avg", "My Attendance", "Class Att", "Status"]
    rows = [[s["course_code"], f"{s['my_marks']:.1f}", f"{s['class_marks']:.1f}", f"{s['my_attendance']:.1f}%", f"{s['class_attendance']:.1f}%", s["status"]] for s in subject_rows]
    return headers, rows


@role_required(["STUDENT", "ADMIN"])
def student_dashboard(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    record = data["record"]
    subject_headers, subject_table_rows = _build_subject_table_rows(data["subject_rows"])
    predicted_gpa_display = f"{record['predicted_gpa']:.2f}" if record["predicted_gpa"] is not None else "Pending"
    rank = data["rank"]
    return render(request, "panels/student_dashboard.html", {
        "page_title": "My Dashboard",
        "active_role": "STUDENT",
        "record": record,
        "risk_status": _risk_status(record["risk_level"]),
        "insight": data["insight"],
        "tips": data["tips"],
        "subject_headers": subject_headers,
        "subject_table_rows": subject_table_rows,
        "chart_data": data["chart"],
        "rank": rank,
        "unread_alerts": data["unread_alerts"],
        "credits": data["credits"],
        "credits_display": f"{data['credits']:.1f}",
        "predicted_gpa_display": predicted_gpa_display,
        "class_standing_display": f"#{rank['rank']} of {rank['total']}" if rank else "N/A",
        "teacher_alerts": data["teacher_alerts"],
        "enrolled_courses": data.get("enrolled_courses", []),
        "admin_contact": data.get("admin_contact", {}),
        "assigned_teacher": data.get("assigned_teacher", {}),
        "db_error": db_error,
    })


@role_required(["STUDENT", "ADMIN"])
def student_report(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    inst_name, term_name = _resolve_pdf_branding(data)
    record = data["record"]
    report_rows = [[s["course_code"], f"{s['my_marks']:.1f}", f"{s['class_marks']:.1f}", f"{s['diff']:+.1f}", f"{s['my_attendance']:.1f}%", s["status"]] for s in data["subject_rows"]]
    return render(request, "panels/student_report.html", {
        "page_title": "My Report Card",
        "active_role": "STUDENT",
        "record": record,
        "risk_status": _risk_status(record["risk_level"]),
        "predicted_gpa_display": f"{record['predicted_gpa']:.2f}" if record["predicted_gpa"] is not None else "Pending",
        "report_headers": ["Course", "My Marks", "Class Avg", "Diff", "Attend.", "Status"],
        "report_rows": report_rows,
        "credits": data["credits"],
        "insight": data["insight"],
        "enrolled_courses": data.get("enrolled_courses", []),
        "admin_contact": data.get("admin_contact", {}),
        "assigned_teacher": data.get("assigned_teacher", {}),
        "portal_institution_name": inst_name,
        "portal_current_term": term_name,
        "db_error": db_error,
    })


@role_required(["STUDENT", "ADMIN"])
def student_report_download(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    if db_error:
        messages.error(request, f"Report download failed: {db_error}")
        return redirect("panels:student_report")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="edupredict_report_card.csv"'
    writer = csv.writer(response)
    writer.writerow(["full_name", "student_id", "batch", "course_code", "my_marks", "class_avg_marks", "my_attendance", "class_avg_attendance", "predicted_gpa", "risk_level", "status"])
    for row in build_report_export_rows(data["record"], data["subject_rows"]):
        writer.writerow(row)
    return response


@role_required(["STUDENT", "ADMIN"])
def student_report_pdf(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    if db_error:
        messages.error(request, f"Report PDF generation failed: {db_error}")
        return redirect("panels:student_report")
    inst_name, term_name = _resolve_pdf_branding(data)
    pdf_data = {**data, "institution_name": inst_name, "current_term": term_name} if isinstance(data, dict) else data
    pdf_bytes = generate_student_report_card_pdf(pdf_data)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    disp = "inline" if request.GET.get("inline") == "1" else "attachment"
    response["Content-Disposition"] = f'{disp}; filename="edupredict_report_card.pdf"'
    return response


@role_required(["STUDENT", "ADMIN"])
def student_tips(request):
    student_id, user_id, role, user = _student_identity(request)
    data, db_error = _safe_context(get_student_overview_context, student_id, user_id, role)
    record = data["record"]
    return render(request, "panels/student_tips.html", {
        "page_title": "Study Tips",
        "active_role": "STUDENT",
        "record": record,
        "risk_status": _risk_status(record["risk_level"]),
        "tips": data["tips"],
        "insight": data["insight"],
        "rank": data["rank"],
        "db_error": db_error,
    })


@role_required(["STUDENT", "ADMIN"])
def student_notifications(request):
    student_id, user_id, role, user = _student_identity(request)
    assigned_teacher = resolve_assigned_teacher(student_id, user_id)
    if request.method == "POST":
        action = str(request.POST.get("action") or "").strip().lower()
        try:
            if action == "mark_read":
                ok, err = mark_alert_read(request.POST.get("alert_id"), student_id, user_id, role)
                messages.success(request, "Alert marked as read.") if ok else messages.error(request, err or "Could not mark alert as read.")
            elif action == "mark_all":
                updated = mark_notifications_read({"user_id": user_id, "student_id": student_id, "role": role})
                messages.success(request, f"{updated} alert(s) marked as read.")
            elif action == "send_feedback":
                if role == "ADMIN":
                    messages.warning(request, "Admins manage help tickets directly and cannot send feedback to themselves.")
                else:
                    recipient = str(request.POST.get("recipient") or "ADMIN").strip().upper()
                    created, err = submit_student_feedback(
                        user_id=user_id,
                        user_name=user.get("full_name") or user.get("email") or "Student",
                        role=role,
                        subject=request.POST.get("subject"),
                        message=request.POST.get("message"),
                        recipient=recipient,
                        target_teacher_id=assigned_teacher.get("teacher_id", ""),
                        target_teacher_name=assigned_teacher.get("name", ""),
                        student_id=student_id,
                    )
                    if created:
                        target_label = f"Teacher ({assigned_teacher.get('name') or 'Assigned'})" if recipient == "TEACHER" else "Institute Admin"
                        messages.success(request, f"Feedback {created['ticket_id']} sent to {target_label}.")
                    else:
                        messages.error(request, err or "Could not send feedback.")
            else:
                messages.error(request, "Unknown alert action.")
        except Exception as exc:
            messages.error(request, f"Action failed: {exc}")
        return redirect("panels:student_notifications")

    data, db_error = _safe_context(get_student_alerts_context, student_id, user_id, role)
    try:
        feedback_tickets = list_student_feedback_tickets(student_id, user_id)
    except Exception:
        feedback_tickets = []
    return render(request, "panels/student_notifications.html", {
        "page_title": "Alerts & Feedback",
        "active_role": "STUDENT",
        "alerts": data["alerts"],
        "feedback_tickets": feedback_tickets,
        "assigned_teacher": assigned_teacher,
        "unread": data["unread"],
        "total": data["total"],
        "db_error": db_error,
    })
